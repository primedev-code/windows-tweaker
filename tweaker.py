import ctypes
import getpass
import os
import platform
import re
import subprocess
import sys

ENCODING = "cp866"  # кодировка вывода консольных утилит Windows
PING_HOST = "8.8.8.8"
E_UNEXPECTED = 0x8000FFFF  # SHEmptyRecycleBinW возвращает это, если корзина уже пуста


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run(cmd):
    """Запускает команду и возвращает CompletedProcess с текстовым выводом."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding=ENCODING,
        errors="replace",
    )


def ps_query(command):
    """Выполняет команду PowerShell и возвращает вывод без лишних пробелов."""
    try:
        process = run(["powershell", "-NoProfile", "-Command", command])
    except FileNotFoundError:
        return ""
    return process.stdout.strip()


def confirm(question):
    """Спрашивает подтверждение у пользователя. True только при ответе y/д."""
    answer = input(f"{question} (y/n): ").strip().lower()
    return answer in ("y", "yes", "д", "да")


def pause(text="\nНажмите Enter чтобы вернуться в главное меню..."):
    input(text)


def format_size(size):
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.1f} {unit}" if unit != "Б" else f"{int(size)} {unit}"
        size /= 1024


def clear_os():
    temp_path = os.environ.get("TEMP")
    if not temp_path or not os.path.exists(temp_path):
        print("[-] Не удалось найти путь к временной папке Temp.")
        pause()
        return

    print(f"Будут удалены файлы из папки: {temp_path}")
    print("Рекомендуется закрыть открытые программы.")
    if not confirm("Продолжить?"):
        print("Отменено.")
        pause()
        return

    deleted = 0
    skipped = 0
    freed = 0

    for root, _dirs, files in os.walk(temp_path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size = os.path.getsize(file_path)
                os.remove(file_path)
                deleted += 1
                freed += size
                print(f"[+] Удален файл {file}")
            except PermissionError:
                skipped += 1
                print(f"[-] Пропущен (занят системой) файл {file}")
            except Exception as e:
                skipped += 1
                print(f"[!] Ошибка при удалении {file}: {e}")

    print("\nПапка Temp обработана!")
    print(f"Удалено файлов: {deleted}, пропущено: {skipped}")
    print(f"Освобождено места: {format_size(freed)}")
    pause()


def check_ping():
    process = run(["ping", "-n", "4", PING_HOST])
    text = process.stdout
    print(text)
    print("-" * 80)

    match = re.search(r"(?:Average|Среднее)\s*=\s*(\d+)\s*(?:ms|мсек)", text)
    if match:
        print(f"Ваш средний пинг: {match.group(1)} мс")
    else:
        print("Интернет отсутствует или превышен интервал ожидания!")

    pause()


def clear_dns():
    process = run(["ipconfig", "/flushdns"])
    if process.returncode == 0:
        print("[+] Кэш DNS успешно очищен!")
    else:
        print(
            "[!] Не удалось очистить кэш. Попробуйте запустить от имени Администратора."
        )
    pause()


def clear_trash():
    print("Очистка корзины необратима: файлы будут удалены безвозвратно.")
    if not confirm("Очистить корзину?"):
        print("Отменено.")
        pause()
        return

    # FLAGS: 7 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
    # Функция не бросает исключение, а возвращает код результата (HRESULT).
    try:
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
    except Exception as e:
        print(f"[!] Не удалось обратиться к корзине: {e}")
        pause()
        return

    result &= 0xFFFFFFFF  # приводим знаковое число к беззнаковому
    if result == 0:
        print("[+] Корзина успешно очищена!")
    elif result == E_UNEXPECTED:
        print("[i] Корзина уже пуста.")
    else:
        print(f"[!] Не удалось очистить корзину (код ошибки: {hex(result)}).")
    pause()


def check_disk():
    output = ps_query(
        "Get-CimInstance -ClassName Win32_DiskDrive | "
        "ForEach-Object { $_.Model + '|' + $_.Status }"
    )

    disks = []
    for line in output.splitlines():
        if "|" in line:
            model, status = line.rsplit("|", 1)
            disks.append((model.strip(), status.strip()))

    if not disks:
        print("[!] Не удалось получить данные о дисках.")
        print("[!] Попробуйте запустить утилиту от имени Администратора.")
        pause()
        return

    all_ok = True
    for model, status in disks:
        ok = status.lower() == "ok"
        all_ok = all_ok and ok
        mark = "[+]" if ok else "[!]"
        print(f"{mark} {model}: {status}")

    print()
    if all_ok:
        print("[+] Проверка завершена, все диски работают исправно!")
    else:
        print("[!] Внимание! Обнаружены проблемы с одним или несколькими дисками.")
        print(
            "[!] Рекомендуется проверить накопитель утилитами вроде CrystalDiskInfo."
        )
    pause()


def system_info():
    try:
        user = os.getlogin()
    except OSError:
        user = getpass.getuser()

    cpu = ps_query(
        "Get-CimInstance -ClassName Win32_Processor | "
        "Select-Object -ExpandProperty Name"
    ) or "Не определено"

    gpu_lines = [
        line.strip()
        for line in ps_query(
            "Get-CimInstance -ClassName Win32_VideoController | "
            "Select-Object -ExpandProperty Name"
        ).splitlines()
        if line.strip()
    ]

    ram_text = ps_query(
        "Get-CimInstance -ClassName Win32_ComputerSystem | "
        "Select-Object -ExpandProperty TotalPhysicalMemory"
    )
    ram = "Не определено"
    if ram_text.isdigit():
        ram = f"{round(int(ram_text) / 1024**3)} ГБ"

    print(f"Пользователь:       {user}")
    print(f"Процессор:          {cpu}")
    print(f"Оперативная память: {ram}")

    if gpu_lines:
        for idx, gpu in enumerate(gpu_lines, 1):
            print(f"Видеокарта {idx}:       {gpu}")
    else:
        print("Видеокарта:         Не определена")

    pause()


MENU = {
    "1": ("Очистить Temp", clear_os),
    "2": ("Проверить пинг", check_ping),
    "3": ("Очистить кэш DNS", clear_dns),
    "4": ("Очистить корзину", clear_trash),
    "5": ("Проверить целостность диска", check_disk),
    "6": ("Информация о ПК", system_info),
}
EXIT_KEY = str(len(MENU) + 1)


def print_menu():
    print("=" * 40)
    print("         SYSTEM TWEAKER & CLEANER")
    print("=" * 40)
    for key, (title, _func) in MENU.items():
        print(f"{key} - {title}")
    print(f"{EXIT_KEY} - Выйти")
    print("=" * 40)


def main():
    if platform.system() != "Windows":
        print("Эта утилита работает только в Windows.")
        sys.exit(1)

    if not is_admin():
        print("[!] Предупреждение: Скрипт запущен без прав администратора.")
        print(
            "    Некоторые функции (очистка DNS/системных Temp) могут работать ограниченно.\n"
        )

    while True:
        print_menu()
        choice = input(f"Выберите действие (1-{EXIT_KEY}): ").strip()
        print("\n")

        if choice == EXIT_KEY:
            print("Завершение работы...")
            break

        action = MENU.get(choice)
        if action:
            action[1]()
        else:
            print("Неверный ввод, попробуйте снова.")


if __name__ == "__main__":
    main()

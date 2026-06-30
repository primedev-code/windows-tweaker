import os
import re
import subprocess

def clear_os():
   temp_path = os.environ.get("TEMP")
   for root, dirs, files in os.walk(temp_path):
      for file in files:
         file_path = os.path.join(root, file)
         try:
            os.remove(file_path)
            print(f"[+] Удален файл {file}")
         except PermissionError:
            print(f"[-] Пропущен (занят системой) файл {file}")
         except Exception as e:
            print(f"[!] Ошибка при удалении {file}: {e}")
   print("Папка Temp успешно очищена!")
   input("Нажмите Enter чтобы вернуться в главное меню...")
   print("\n" * 40)
def check_ping():
   result = subprocess.run(["ping", "-n", "4", "8.8.8.8"], capture_output=True, text=True, encoding="cp866")
   text = result.stdout
   print(text)
   print("\n" * 1)
   print("-" * 80)
   print("\n" * 1)
   sample = r"Average\s*=\s*(\d+)\s*ms"
   sample1 = r"Среднее\s*=\s*(\d+)\s*мсек"
   result_search = re.search(sample, text)
   result_search1 = re.search(sample1, text)
   if result_search:
          digit = result_search.group(1)
          print(f"Ваш средний пинг: {digit} мс")
   elif result_search1:
          digit = result_search1.group(1)
          print(f"Ваш средний пинг: {digit} мс")
   else:
      print("Интернет отсутствует, проверьте подключенние к сети!")
   print("\n")
   print("-" * 80)
   input("Нажмите Enter чтобы вернуться в главное меню...")
   print("\n" * 40)
def main():
   while True:
      print("1 - очистить Temp")
      print("2 - проверить пинг")
      print("3 - выйти")
      choice = input("Выберете действие: ")
      if choice == "1":
         clear_os()
      elif choice == "2":
         check_ping()
      elif choice == "3":
         break


if __name__ == "__main__":
   main()

import os, aiohttp, asyncio, argparse
from bs4 import BeautifulSoup
from time import sleep, strftime, localtime

def current_time():
    return strftime("%Y-%m-%d %H:%M:%S", localtime())

class AutoClickAPI:
    def __init__(self, email: str = None, password: str = None, timeout: int = None, filename: str = 'options.txt'):
        if email and password:
            self.email = email
            self.password = password
            self.timeout = timeout if timeout else 30
        else:
            options = {}
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    for line in file:
                        clean_line = line.split('#')[0].strip()
                        if not clean_line or '=' not in clean_line: continue
                        key, value = clean_line.split('=', 1)
                        options[key.strip()] = value.strip()
            except FileNotFoundError:
                raise FileNotFoundError(f"Файл конфигурации '{filename}' не найден")

            if 'login' not in options or 'password' not in options:
                raise ValueError("Укажите в файле конфигурации параметры 'login' и 'password'")
            else:
                self.email = options['login']
                self.password = options['password']

            if 'timeout' in options: self.timeout = int(options['timeout'])
            else: self.timeout = 30

    async def login(self) -> bool:
        AUTH = f'https://lk.sut.ru/cabinet/lib/autentificationok.php?users={self.email}&parole={self.password}'
        CABINET = 'https://lk.sut.ru/cabinet/'

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
                async with session.get(f'{CABINET}?login=no') as response:
                    response.raise_for_status()
                    self.cookies = response.cookies
                    async with session.post(AUTH) as response:
                        response.raise_for_status()
                        text = await response.text()
                        if text == '1':
                            async with session.get(f'{CABINET}?login=yes') as response:
                                response.raise_for_status()
                                print(f'[{current_time()}] login: успешная авторизация')
                                return True
                        else:
                            print(f'[{current_time()}] login: ошибка при авторизации')
                            return False
        except Exception as e:
            print(f'[{current_time()}] auto_click: ошибка при подключении | {type(e).__name__} {e}')
            print(f'[{current_time()}] login: timeout {self.timeout} перед следующей попыткой авторизации')
            sleep(self.timeout)
            return False

    async def auto_click(self):
        URL = 'https://lk.sut.ru/cabinet/project/cabinet/forms/raspisanie.php'
        ERR_MSG = "У Вас нет прав доступа. Или необходимо перезагрузить приложение.."

        response = False
        while not response:
            response = await self.login()

        while True:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
                    async with session.get(URL, cookies=self.cookies) as response:
                        response.raise_for_status()
                        text = await response.text()
                        if text == ERR_MSG:
                            print(f'[{current_time()}] auto_click: срок сессии истёк')
                            response = False
                            while not response:
                                response = await self.login()
                            continue

                        soup = BeautifulSoup(text, 'html.parser')
                        week = soup.find("h3").text.split("№")[1].split()[0]
                        knop_ids = tuple(x['id'][4:] for x in soup.find_all('span') if x.get('id', '').startswith('knop'))

                        for lesson_id in knop_ids:
                            async with session.post(f'{URL}?open=1&rasp={lesson_id}&week={week}', cookies=self.cookies) as response:
                                print(f'[{current_time()}] auto_click: отправлен запрос для начала занятия по id: {lesson_id}')
                        else:
                            print(f'[{current_time()}] auto_click: нет активных занятий')
            except Exception as e:
                print(f'[{current_time()}] auto_click: ошибка при подключении | {type(e).__name__} {e}')
            finally:
                print(f'[{current_time()}] auto_click: timeout {self.timeout} секунд перед следующим циклом')
                sleep(self.timeout)

    @staticmethod
    def get_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser()
        parser.add_argument("login", nargs='?', help="email used for logging in to lk.sut")
        parser.add_argument("password", nargs='?', help="password used for logging in to lk.sut")
        parser.add_argument("-t", "--timeout", type=int, default=None, help="timeout in seconds between auto-click cycles")
        args = parser.parse_args()
        return args

    @staticmethod
    def cls():
        os.system('cls' if os.name=='nt' else 'clear')

if __name__ == '__main__':
    '''
    Запустите программу с аргументами в CLI:
        python3 auto_click.py <login> <password> -t <timeout>

    Либо создайте `options.txt` с параметрами:
        # Обязательные параметры
        login=your_login       # Логин для автопосещения
        password=your_password # Пароль для автопосещения

        # Опциональные параметры
        timeout=60             # Задержка перед следующей проверкой занятий (в секундах)
    '''

    args = AutoClickAPI.get_args()
    AutoClickAPI.cls()
    if args.login and args.password:
        api = AutoClickAPI(args.login, args.password, timeout=args.timeout)
    else:
        api = AutoClickAPI(filename='options.txt')
    asyncio.run(api.auto_click())
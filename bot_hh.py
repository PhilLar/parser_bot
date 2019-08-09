import telebot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, ForceReply
import re
import requests
from bs4 import BeautifulSoup as bs
from bs4 import SoupStrainer
from const import AREA_URL, HEADERS, BASE_URL, HEADERS, TOKEN



class bot_hh(telebot.TeleBot):
    def __init__(self, token):
        super().__init__(token)
        self.cities = {'Санкт-Петербург':'spb', 'Москва':'', 'Новосибирск':'novosibirsk'}
        self.vacancies = []
        self.default_cities = ['Москва', 'Санкт-Петербург', 'Новосибирск']
        self.default_periods = []
        self.steps = {'city': None, 'position': None, 'period': None}

    def _set_handles(self):

        @self.message_handler(commands=['start'])
        def send_welcome(message: Message):
            for i in self.steps: self.steps[i] = None
            self.reply_to(message, 'Выберите город для поиска вакансии', parse_mode='Markdown', reply_markup=self.markup_cities)

        @self.message_handler(func=lambda message: message.text in self.cities.keys() and
                                                   self.steps['position'] is None and
                                                   self.steps['city'] is None)
        def request_position(message: Message):
            self.steps['city'] = self.cities[message.text]
            self.reply_to(message, 'Пожалуйста, введите название должности', reply_markup=self.markup_start)

        @self.message_handler(func=lambda message: self.steps['city'] is not None and
                                                   self.steps['position'] is None and
                                                   self.steps['period'] is None)
        def request_period(message: Message):
            self.steps['position'] = message.text
            self.reply_to(message, 'Пожалуйста, введите срок публикации вакансии', reply_markup=self.markup_periods)

        @self.message_handler(func=lambda message: self.steps['position'] is not None and
                                                   self.steps['city'] is not None and
                                                   str.isdigit(message.text))
        def show_vacancies(message: Message):
            self.steps['period'] = message.text
            vacs = self._parse_vacancies(city=self.steps['city'], position=self.steps['position'],
                                            period=self.steps['period'])
            if vacs:
                for vac in vacs:
                    post = vac['title'] + '\n' + vac['reqs'] + '\n' + vac['respbs'] + '\n' + vac['url'] + '\n'
                    self.reply_to(message, post, reply_markup=self.markup_start)
            else:
                self.reply_to(message, 'По вашему запросу ничего не найдено!(', reply_markup=self.markup_start)


    def _create_markup(self):
        btn_start = KeyboardButton('/start')
        self.markup_start = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        self.markup_start.add(btn_start)
        # DEFAULT AVAILABLE CITIES
        self.markup_cities =  ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        btn_spb = KeyboardButton('Санкт-Петербург')
        btn_msc = KeyboardButton('Москва')
        btn_nsk = KeyboardButton('Новосибирск')
        self.markup_cities.row(btn_spb, btn_msc, btn_nsk)
        self.markup_cities.row(btn_start)
        # VACANCY PERIOD
        self.markup_periods =  ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        btn_day = KeyboardButton('1')
        btn_week = KeyboardButton('7')
        btn_month = KeyboardButton('30')
        btn_start = KeyboardButton('/start')
        self.markup_periods.row(btn_day, btn_week, btn_month)
        self.markup_periods.row(btn_start)
    
    # def parse_cities_with_soup(self, area_url=AREA_URL):
    #     #start = time.time()
    #     session = requests.Session()
    #     req = session.get(area_url, headers=self.headers)
    #     if req.status_code == 200:
    #         data = SoupStrainer('a')
    #         str_req = req.text
    #         soup = bs(str_req, 'html.parser', parse_only=data)
    #         hrefs = soup.find_all('a')
    #     for i in hrefs:
    #         x = re.search("https://(.+?).hh", i['href'])
    #         if x:
    #             self.cities[i.text] = x.group(1)
    #     #print(time.time()- start)
    
    # unlike with soup, with regex parse is twice faster
    def _parse_cities(self, area_url=AREA_URL):
        #start = time.time()
        session = requests.Session()
        req = session.get(area_url, headers=HEADERS)
        if req.status_code == 200:
            str_req = req.text
            all_a = re.findall('<a(.+?)/a>', str_req)
            for a in all_a:
                key = re.search(">(.+?)<", a)
                val = re.search("https://(.+?).hh", a)
                if key and val:
                    self.cities[key.group(1)] = val.group(1)
        #print(time.time()-start)
    
    def _parse_vacancies(self, position, period=1, city='', page=0):
        if city == '':
            base_url = f'https://hh.ru/search/vacancy?search_period={period}&area=2&text={position}&page={page}'
        else:
            base_url = f'https://{city}.hh.ru/search/vacancy?search_period={period}&area=2&text={position}&page={page}'
        session = requests.Session()
        req = session.get(base_url, headers=HEADERS)
        if req.status_code == 200:
            soup = bs(req.content, 'html.parser')
            divs = soup.find_all('div', attrs={"data-qa": "vacancy-serp__vacancy"})
            vacancies = []
            for div in divs:
                if div:
                    a = div.find(('a', {'data-qa':'vacancy-serp__vacancy-title'}))
                    title = a.text
                    url_vac = a['href']
                    requirements = div.find('div', {'data-qa':'vacancy-serp__vacancy_snippet_responsibility'}).text
                    responsibilities = div.find('div', {'data-qa':'vacancy-serp__vacancy_snippet_requirement'}).text
                    vacancies.append({
                        'title': title,
                        'url': url_vac,
                        'reqs': requirements,
                        'respbs': responsibilities
                    })
            return vacancies
    

    def setup(self):
        self._parse_cities()
        self._create_markup()
        self._set_handles()
        self.polling(none_stop=True)

if __name__ == '__main__':
    bot = bot_hh(TOKEN)
    bot.setup()
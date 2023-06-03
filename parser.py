import psycopg2
import requests
import asyncio
from bs4 import BeautifulSoup


async def do_parse():
    url = 'https://ria.ru'

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36'
    }

    req = requests.get(url, headers=headers)
    soup = BeautifulSoup(req.text, 'lxml')

    soup_href = soup.find_all('a', class_='cell-list__item-link color-font-hover-only')
    href_url = []
    for item in soup_href:
        href_url.append([item.get('title'), item.get('href')])

    for index in range(len(href_url)):
        url = href_url[index][1]
        headers = {
            'Accept': '*/*',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36'
        }
        # Собираю текст с каждой ссылки
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.text, 'lxml')
        post = soup.find_all('div', class_='article__text')
        post_text = [x.text for x in post]
        post_text_join = ''.join(post_text)
        post_text_join_corr = post_text_join.replace("'", '"')
        href_url[index].append(post_text_join_corr)
        # Собираю дату публикации
        post_add_time = soup.find_all('div', class_='article__info-date')
        post_add_time_text = [x.text.replace('\n', '').split()[:2][::-1] for x in post_add_time]
        href_url[index].append(' '.join(post_add_time_text[0]))

    con = psycopg2.connect(
        database="parse_news",
        user="postgres",
        password="admin",
        host="localhost",
        port="5432"
    )
    print('Успешное подключение к базе')
    cur = con.cursor()
    cur.execute(
        'CREATE TABLE IF NOT EXISTS ria_news_table (id serial PRIMARY KEY, add_date timestamp, title CHARACTER VARYING(500), url_href CHARACTER VARYING(300), text VARCHAR)')

    cur.execute('SELECT COUNT(*) FROM ria_news_table')  # Проверка, есть ли записи в базе
    answer = cur.fetchall()

    if answer[0][0]:  # пополнение базы только новыми статьями которых нет в БД
        cur.execute('SELECT * FROM ria_news_table')
        rows = cur.fetchall()
        title_list = [row[:][2] for row in rows]

        for index in range(len(href_url)):
            if not href_url[index][0] in title_list:
                cur.execute(
                    f"INSERT INTO ria_news_table (add_date, title, url_href, text) VALUES ('{href_url[index][3]}', "
                    f"'{href_url[index][0]}', '{href_url[index][1]}','{href_url[index][2]}')")
    else:   # вставка новостей если БД пустая
        for index in range(len(href_url)):
            cur.execute(
                f"INSERT INTO ria_news_table (add_date, title, url_href, text) VALUES ('{href_url[index][3]}', "
                f"'{href_url[index][0]}', '{href_url[index][1]}','{href_url[index][2]}')")

    con.commit()
    cur.close()
    con.close()
    print('Запись завершена')
    return 0


#asyncio.run(do_parse())

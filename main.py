from flask import Flask, request
import logging
import random
import requests
import json


class User:
    def __init__(self, user_id):
        self.id = user_id
        self.answering = False
        self.prev_q = ""
        self.prev_a = ""
        self.buttons = []
        self.animes = []
        self.cur_anime = ""
        self.save = False

    def add_anime(self, id):
        self.animes.append((id))
        self.cur_anime = Anime(id)

    def get_animes(self):
        return self.animes


class Anime:
    def __init__(self, id_):
        self.id = id_

    def get_anime(self, addition=""):
        return requests.get("https://shikimori.org/api/animes/" + str(self.id) + addition, headers=headers).json()


def image(url):
    r = requests.get("https://shikimori.org/" + url,
                     headers={"User-Agent": "cb1ffadb48a24a42fba0ab94475d38b337852671137457df8f69da86ee888c0b"})

    f = {"file": r.content}

    return requests.post("https://dialogs.yandex.net/api/v1/skills/4be97f7a-f911-41be-90a4-36c4269647e4/images",
                         files=f, headers={"Authorization": "OAuth AQAAAAAg1GXEAAT7oydYIgkv-0-EkrYRD-ok6CE",
                         "Content - Type": "multipart / form - data"}).json()['image']['id']


app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

token = "cb1ffadb48a24a42fba0ab94475d38b337852671137457df8f69da86ee888c0b"

sessionStorage = {}
headers = {
    "User-Agent": token
}
commands = [
    "о навыке",
    "дай аниме",
    "дай аниме по",
    "информация",
    "похожие на",
    "топ аниме по",
    "все аниме озвученные",
    "франшиза",
    "следуйщие серии"
]


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)

    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }

    handle_dialog(request.json, response)

    logging.info('Response: %r', request.json)
    print(response)
    return json.dumps(response)


def handle_dialog(req, res):
    user_id = req['session']['user_id']

    if req['session']['new']:
        sessionStorage[user_id] = User(user_id)
        sessionStorage[user_id].buttons = ["О навыке"]
        res['response']['text'] = 'Привет! Запущен навык Аниме'
        res['response']['buttons'] = get_suggests(user_id)
        return
    command = req['request']['original_utterance'].lower()
    if command == "повтори":
        command = sessionStorage[user_id].prev_q
    if command == "сброс":
        sessionStorage[user_id] = User(user_id)
        write(res, "сброшено", user_id)
        return
    if sessionStorage[user_id].answering:
        prev = sessionStorage[user_id].prev_q
        if prev == "дай аниме по":
            genre = req['request']['original_utterance']
            gens = requests.get("https://shikimori.org/api/genres", headers=headers).json()
            if genre == "все":
                js = requests.get("https://shikimori.org/api/animes" + "?page=" +
                                  str(random.randint(1, 100)), headers=headers).json()
            else:
                gen_id = ""
                for g in gens:
                    if g["russian"].lower() == genre:
                        gen_id = g['id']
                        break
                js = requests.get("https://shikimori.org/api/animes?genre=" + str(gen_id) + "&page=" +
                                  str(random.randint(1, 100)), headers=headers).json()
            id_ = js[random.randint(1, 49)]["id"]
            sessionStorage[user_id].add_anime(id_)
            jsonfil = sessionStorage[user_id].get_anime()
            write(res, str(jsonfil["name"]) + "/" + str(jsonfil["russian"]) + " " + str(
                jsonfil["kind"]).upper() + " " + str(jsonfil["episodes_aired"]) + "/" +
                  str(jsonfil["episodes"]), user_id)
            sessionStorage[user_id].answering = False
            return
        elif prev == "информация":
            anime = req['request']['original_utterance']
            js = requests.get("https://shikimori.org/api/animes?search=" + anime,
                              headers=headers).json()[0]
            id_ = js['id']
            sessionStorage[user_id].add_anime(id_)
            info = sessionStorage[user_id].cur_anime.get_anime()
            genres = ""
            for g in info['genres']:
                genres += g['russian'] + ", "
            genres = genres[:-1]
            write(res, '''
                                Название: {}/{}
                                Дата анонса: {}
                                Жанры: {}
                                Количество серии: {}
                                Вышло серии: {}
                                Ограничение: {}
                                Рейтинг: {}
                                '''.format(str(info['russian']), str(info['name']), str(info['aired_on']), genres,
                                           str(info['episodes']), str(info['episodes_aired']), info['rating'],
                                           str(info['score'])),
                  user_id, image=image(js["image"]['original']))
            sessionStorage[user_id].answering = False
            return
        elif prev == "похожине на":
            anime = req['request']['original_uttarence']
            id_ = requests.get("https://shikimori.org/api/animes?search=" + anime,
                               headers=headers).json()[0]['id']
            sessionStorage[user_id].add_anime(id_)
            js = sessionStorage[user_id].cur_anime.get_anime(addition="/similar")
            text = "Похожие:"
            i = 0
            for an in js:
                i += 1
                print(i)
                text += "\n" + an["russian"] + "/" + an["name"]
            write(res, text, user_id)
            sessionStorage[user_id].answering = False
            return
        elif prev == "топ аниме по":
            inp = req['request']['original_utterance'].split()
            genre = inp[0]
            x = inp[1]
            try:
                gens = requests.get("https://shikimori.org/api/genres", headers=headers).json()
                gen_id = ""
                for g in gens:
                    if g['russian'].lower() == genre and g['kind'] == "anime":
                        gen_id = g['id']
                        break
                print(gen_id, x)
                js = requests.get(
                    "https://shikimori.org/api/animes?genre=" + str(gen_id) + "&limit=" + str(int(x) + 1),
                    headers=headers
                ).json()
                res['response']['text'] = "Топ " + x + " аниме по жанру " + genre
                for i in range(int(x)):
                    print(i, js)
                    res['response']['text'] += "\n" + str(i + 1) + ")" + js[i]["russian"]
                res['response']['buttons'] = get_suggests(user_id)
                return
            except ValueError:
                write(res, "Ошибка. Жанр " + genre + " не существует. Попробуйте снова", user_id)
                return
            except IndexError:
                write(res, "Ошибка. Попробуйте другой жанр", user_id)
                return
        elif prev == "франшиза":
            anime = req['request']['original_utterance']
            id_ = requests.get("https://shikimori.org/api/animes?search=" + anime,
                               headers=headers).json()[0]['id']
            franchises = franchise(id_)
            if franchises is not None:
                text = "Аниме которые принадлежат франшизе:"
                for i in range(len(franchises)):
                    text += "/n" + str(i + 1) + ")" + franchises[i]["name"] + " " + franchises[i]["kind"]
                write(res, text, user_id)
                return
            else:
                text = "Введенное аниме не нашлось"
                write(res, text, user_id)
                return
        elif prev == "следуйщие серии":
            x = int(req['request']['original_utterance'])
            js = requests.get("https://shikimori.org/api/calendar", headers=headers).json()
            if x == 1:
                cur = js[0]
                text = "Следуйщяя серия: " + cur['anime']['russian'] + " эпизод " + cur['next_episode'] + " в " + cur['next_episode_at']
                write(res, text, user_id, image=image(cur['image']['original']))
            else:
                text = "Скоро выйдут:"
                for i in range(x):
                    cur = js[i]
                    text += "\n" + str(i + 1) + ")" + str(cur['anime']['russian']) + " эпизод " + str(cur['next_episode']) + " в " + str(cur['next_episode_at'])
                write(res, text, user_id)
            return
        else:
            write(res, "Напишите снова или напишите 'Сброс' для того чтоб начать сначала", user_id)
        sessionStorage[user_id].answering = False
    if command in commands:
        index = commands.index(command)
        sessionStorage[user_id].prev_q = command
        if index == 0:
            sessionStorage[user_id].buttons = ["Дай аниме", "Дай аниме по", "Топ аниме по",
                                               "Информация", "Похожие на",
                                               "Повтори", "Франшиза", "Cледуйщие серии"]
            text = 'Доступные команды:\n1)Дай аниме(Рандомное аниме из списка)\n2)Дай аниме' \
                   ' по (жанрам)\n3)Топ по жанрам\n4)Информация\n5)' \
                   'Похожие на\n5)Все аниме озвученные\n6)Франшиза\n7)Следуйщие серии'
            write(res, text, user_id)
            return
        elif index == 1:
            js = requests.get("https://shikimori.org/api/animes?page=" + str(random.randint(1, 100)),
                              headers=headers).json()
            id_ = js[0]["id"]
            sessionStorage[user_id].add_anime(id_)
            logging.info('Index: %r', id_)
            jsonfil = sessionStorage[user_id].cur_anime.get_anime()
            write(res, str(jsonfil["name"]) + "/" + str(jsonfil["russian"]) + " " +
                  str(jsonfil["kind"]).upper() + " " + str(jsonfil["episodes_aired"]) +
                  "/" + str(jsonfil["episodes"]), user_id, image=image(jsonfil["image"]["original"]), buttons=[{'title': 'Перейти', 'hide': True, 'url': "https://shikimori.org/" + jsonfil['url']}])
            return
        elif index == 2:
            text = "Напиши название жанра"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 3:
            text = "Напиши название аниме(на английском)"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 4:
            text = "Напиши название аниме(на английском)"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 5:
            text = "Напиши жанр потом количество"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 6:
            text = "Все аниме которые были написаны в этой беседе:"
            for index, anime in enumerate(sessionStorage[user_id].animes):
                jsonfil = requests.get("https://shikimori.org/api/animes/" + str(anime), headers=headers).json()
                text += "\n" + str(index) + ")" + jsonfil["russian"]
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 7:
            text = "Напиши название аниме(на английском)"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
        elif index == 8:
            text = "Введите кол-во серии которые вы хотите увидеть"
            write(res, text, user_id)
            sessionStorage[user_id].answering = True
            return
    else:
        res['response']['text'] = 'Неверная команда. Для получения информации напишите "О навыке"'
        res['response']['buttons'] = get_suggests(user_id)
        return


def write(res, text, user_id, image="", buttons=[]):
    res['response']['text'] = text
    if buttons is []:
        res['response']['buttons'] = get_suggests(user_id)
    else:
        res['response']['buttons'] = buttons
    if image is not "":
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']["card"]['image_id'] = image
        res['response']['card']['title'] = text


def get_suggests(user_id):
    session = sessionStorage[user_id]

    suggests = [
        {'title': suggest, 'hide': True}
        for suggest in session.buttons
    ]

    return suggests


def franchise(id_):
    try:
        js = requests.get("https://shikimori.org/api/animes/" + id_ + "/franchise").json()
        return js["nodes"]
    except Exception:
        return None


if __name__ == '__main__':
    app.run(port=31373)

import re
import random
from flask import Flask, render_template, request
from faker import Faker

app = Flask(__name__)
fake = Faker()


images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c', '2d2ab7df-cdbc-48a8-a936-35bba702def5', 
              '6e12f3de-d5fd-4ebb-855b-8cbc485278b7', 'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728', 
              'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_post(i):
    return {
        'title': f'Пост №{i+1}',
        'text': fake.paragraph(nb_sentences=20),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-1y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': [] 
    }

posts_list = [generate_post(i) for i in range(5)]

#марш

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list)

@app.route('/posts/<int:index>')
def post(index):
    p = posts_list[index]
    return render_template('post.html', title=p['title'], post=p)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

#марш 2

@app.route('/request-data', methods=['GET', 'POST'])
def request_data():
    url_params = request.args
    headers = request.headers
    cookies = request.cookies
    form_data = request.form if request.method == 'POST' else None
    return render_template('request_data.html', url_params=url_params, headers=headers, cookies=cookies, form_data=form_data)

@app.route('/phone-check', methods=['GET', 'POST'])
def phone_check():
    phone = ""
    error_msg = None
    formatted_phone = None
    if request.method == 'POST':
        phone = request.form.get('phone', '')
        if not re.match(r'^[0-9\s\(\)\-\.\+]+$', phone):
            error_msg = "Недопустимый ввод. В номере телефона встречаются недопустимые символы."
        else:
            digits = re.sub(r'\D', '', phone)
            length = len(digits)
            is_russian = phone.startswith('+7') or phone.startswith('8')
            if (is_russian and length != 11) or (not is_russian and length != 10):
                error_msg = "Недопустимый ввод. Неверное количество цифр."
            else:
                d = digits[-10:]
                formatted_phone = f"8-{d[:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"
    return render_template('phone_check.html', error_msg=error_msg, phone=phone, formatted_phone=formatted_phone)

if __name__ == '__main__':
    app.run(debug=True)
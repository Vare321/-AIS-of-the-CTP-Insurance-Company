from flask import Flask
from models import db, Policy
import os
from sqlalchemy import text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///osago.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    try:
        # Проверяем, существует ли столбец
        result = db.session.execute(text("PRAGMA table_info(policy)")).fetchall()
        columns = [row[1] for row in result]
        
        if 'notes' not in columns:
            # Добавляем столбец notes
            db.session.execute(text("ALTER TABLE policy ADD COLUMN notes TEXT"))
            db.session.commit()
            print('База данных успешно обновлена: добавлен столбец notes в таблицу policy')
        else:
            print('Столбец notes уже существует в таблице policy')
    except Exception as e:
        print(f'Ошибка при обновлении базы данных: {str(e)}')

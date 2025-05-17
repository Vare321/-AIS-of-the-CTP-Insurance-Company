from flask import Flask, send_file, url_for
from pywebio.platform.flask import webio_view
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
from models import db, User, Client, Vehicle, Policy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
from datetime import datetime, timedelta
import threading
from fpdf.enums import XPos, YPos

app = Flask(__name__)
_thread_locals = threading.local()

def get_username():
    """Безопасное получение имени пользователя из локального хранилища потока"""
    try:
        return _thread_locals.username
    except AttributeError:
        # Если username не установлен, перенаправляем на логин
        return None

def go_to_main_menu():
    """Функция для перехода на главную страницу"""
    main_menu()

app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///osago.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'files')

# Создаем директорию для временных файлов, если она не существует
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db.init_app(app)

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    # Создание тестового пользователя, если его нет
    if not User.query.filter_by(username='admin').first():
        test_user = User(
            username='admin',
            password=generate_password_hash('admin'),
            role='admin'
        )
        db.session.add(test_user)
        db.session.commit()

def validate_passport(passport):
    """Валидация паспортных данных"""
    # Проверка формата: 1234 567890
    if len(passport.replace(" ", "")) != 10 or not passport.replace(" ", "").isdigit():
        return "Паспорт должен содержать 10 цифр"
    return None

def validate_phone(phone):
    """Валидация телефонного номера"""
    if phone and (not phone.startswith('+') or not phone[1:].isdigit()):
        return "Телефон должен начинаться с '+' и содержать только цифры"
    return None

def validate_email(email):
    """Простая валидация email"""
    if email and '@' not in email:
        return "Email должен содержать символ '@'"
    return None

def validate_vin(vin):
    """Валидация VIN-кода"""
    if len(vin) != 17:
        return "VIN должен содержать 17 символов"
    return None

def validate_reg_number(reg_number):
    """Валидация государственного номера автомобиля"""
    # Простая проверка на минимальную длину
    if len(reg_number) < 6:
        return "Государственный номер слишком короткий"
    return None

def main_menu(username=None):
    clear()
    
    # Если имя пользователя не передано, пытаемся получить его из thread_locals
    if username is None:
        username = get_username()
    
    # Если имя пользователя все еще None, перенаправляем на страницу логина
    if username is None:
        login()
        return
    
    put_markdown(f"# АИС Страховой компании ОСАГО")
    put_markdown(f"Добро пожаловать, {username}!")
    
    choices = [
        'Добавить клиента',
        'Список клиентов',
        'Добавить транспортное средство',
        'Список транспортных средств',
        'Оформить полис ОСАГО',
        'Список полисов',
        'Статистика и аналитика',
        'Уведомления о полисах',
        'Выход'
    ]
    
    while True:
        choice = actions("Выберите действие:", choices)
        
        if choice == 'Добавить клиента':
            add_client()
        elif choice == 'Список клиентов':
            list_clients()
        elif choice == 'Добавить транспортное средство':
            add_vehicle()
        elif choice == 'Список транспортных средств':
            list_vehicles()
        elif choice == 'Оформить полис ОСАГО':
            # Отображаем список ТС для выбора полиса для оформления
            list_vehicles_for_policy()
        elif choice == 'Список полисов':
            list_policies()
        elif choice == 'Статистика и аналитика':
            show_statistics()
        elif choice == 'Уведомления о полисах':
            check_expiring_policies()
        elif choice == 'Выход':
            clear()
            login()
            break

def login():
    with app.app_context():
        info = input_group("Вход в систему", [
            input("Имя пользователя", name="username", required=True),
            input("Пароль", name="password", type=PASSWORD, required=True)
        ])
        
        user = User.query.filter_by(username=info['username']).first()
    
    if user and check_password_hash(user.password, info['password']):
        clear()
        _thread_locals.username = user.username
        main_menu(_thread_locals.username)
    else:
        clear()
        put_error("Неверные учетные данные")
        login()

def add_client():
    while True:
        info = input_group("Добавление нового клиента", [
            input("ФИО", name="full_name", required=True),
            input("Серия и номер паспорта", name="passport", required=True, 
                  help_text="Формат: 1234 567890"),
            input("Телефон", name="phone", help_text="Формат: +79001234567"),
            input("Email", name="email", help_text="Формат: example@mail.ru")
        ])
        
        # Валидация данных
        errors = []
        passport_error = validate_passport(info['passport'])
        if passport_error:
            errors.append(passport_error)
            
        phone_error = validate_phone(info['phone'])
        if phone_error and info['phone']:
            errors.append(phone_error)
            
        email_error = validate_email(info['email'])
        if email_error and info['email']:
            errors.append(email_error)
            
        if errors:
            clear()
            for error in errors:
                put_error(error)
            continue  # Повторяем ввод данных
            
        with app.app_context():
            # Проверка на существование паспорта в базе данных
            existing_client = Client.query.filter_by(passport=info['passport']).first()
            if existing_client:
                clear()
                put_error(f"Клиент с паспортом {info['passport']} уже существует")
                continue  # Повторяем ввод данных
                
            try:
                client = Client(**info)
                db.session.add(client)
                db.session.commit()
                clear()
                put_success(f"Клиент {info['full_name']} успешно добавлен")
                break  # Выход из цикла
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при добавлении клиента: {str(e)}")
                continue  # Повторяем ввод данных
    
    main_menu(_thread_locals.username)

def list_clients():
    with app.app_context():
        clients = Client.query.all()
    
    if not clients:
        put_warning("Список клиентов пуст")
        return
    
    # Добавляем поле поиска
    search_term = input("Поиск по ФИО или паспорту:", placeholder="Введите данные для поиска")
    
    filtered_clients = clients
    if search_term:
        # Фильтруем список клиентов
        filtered_clients = [c for c in clients if search_term.lower() in c.full_name.lower() or 
                           search_term in c.passport]
        
    if not filtered_clients:
        put_warning("Клиенты не найдены")
        put_button("Назад", onclick=lambda: main_menu(_thread_locals.username))
        return
    
    table = [['ID', 'ФИО', 'Паспорт', 'Телефон', 'Email', 'Действия']]
    for client in filtered_clients:
        table.append([
            client.id,
            client.full_name,
            client.passport,
            client.phone or '-',
            client.email or '-',
            put_buttons(['Подробнее', 'Редактировать', 'Удалить'], 
                      [lambda c_id=client.id: show_client_details(c_id), 
                       lambda c_id=client.id: edit_client(c_id), 
                       lambda c_id=client.id: delete_client(c_id)])
        ])
    
    put_table(table)
    put_button("Назад", onclick=lambda: main_menu(_thread_locals.username))

def show_client_details(client_id):
    with app.app_context():
        result = (Client.query
                 .options(db.joinedload(Client.vehicles))
                 .filter(Client.id == client_id)
                 .first())
    
    if not result:
        put_error("Клиент не найден")
        return
    
    clear()
    put_markdown(f"# Информация о клиенте")
    put_table([
        ['ФИО', result.full_name],
        ['Паспорт', result.passport],
        ['Телефон', result.phone or '-'],
        ['Email', result.email or '-']
    ])
    
    put_markdown("## Транспортные средства клиента")
    if result.vehicles:
        vehicles_table = [['Марка', 'Модель', 'Год', 'VIN', 'Гос. номер']]
        for vehicle in result.vehicles:
            vehicles_table.append([
                vehicle.brand,
                vehicle.model,
                vehicle.year,
                vehicle.vin,
                vehicle.reg_number
            ])
        put_table(vehicles_table)
    else:
        put_warning("У клиента нет зарегистрированных ТС")
    
    put_button("Назад", onclick=lambda: main_menu(_thread_locals.username))

def edit_client(client_id):
    """Редактирование информации о клиенте"""
    with app.app_context():
        client = db.session.get(Client, client_id)
        if not client:
            put_error("Клиент не найден")
            return
    
    clear()
    put_markdown(f"# Редактирование клиента {client.full_name}")
    
    while True:
        info = input_group("Редактирование данных клиента", [
            input("ФИО", name="full_name", required=True, value=client.full_name),
            input("Серия и номер паспорта", name="passport", required=True, value=client.passport,
                 help_text="Формат: 1234 567890"),
            input("Телефон", name="phone", value=client.phone or "",
                 help_text="Формат: +79001234567"),
            input("Email", name="email", value=client.email or "",
                 help_text="Формат: example@mail.ru")
        ])
        
        # Валидация данных
        errors = []
        passport_error = validate_passport(info['passport'])
        if passport_error:
            errors.append(passport_error)
            
        phone_error = validate_phone(info['phone'])
        if phone_error and info['phone']:
            errors.append(phone_error)
            
        email_error = validate_email(info['email'])
        if email_error and info['email']:
            errors.append(email_error)
            
        if errors:
            clear()
            for error in errors:
                put_error(error)
            continue
        
        with app.app_context():
            # Проверка на существование паспорта в базе данных (у других клиентов)
            existing_client = Client.query.filter(
                Client.passport == info['passport'], 
                Client.id != client_id
            ).first()
            
            if existing_client:
                clear()
                put_error(f"Клиент с паспортом {info['passport']} уже существует")
                continue
            
            try:
                client.full_name = info['full_name']
                client.passport = info['passport']
                client.phone = info['phone']
                client.email = info['email']
                db.session.commit()
                clear()
                put_success(f"Данные клиента {client.full_name} успешно обновлены")
                break
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при обновлении данных: {str(e)}")
                continue
    
    show_client_details(client_id)

def delete_client(client_id):
    """Удаление клиента из базы данных"""
    with app.app_context():
        client = db.session.get(Client, client_id)
        if not client:
            put_error("Клиент не найден")
            return
        
        # Проверка наличия транспортных средств у клиента
        vehicles = Vehicle.query.filter_by(client_id=client_id).all()
    
    clear()
    put_markdown(f"# Удаление клиента {client.full_name}")
    
    if vehicles:
        put_error("Невозможно удалить клиента, так как у него есть зарегистрированные транспортные средства.")
        put_markdown("Сначала необходимо удалить все транспортные средства клиента.")
        
        vehicles_table = [['ID', 'Марка', 'Модель', 'Год', 'VIN', 'Гос. номер']]
        for vehicle in vehicles:
            vehicles_table.append([
                vehicle.id,
                vehicle.brand,
                vehicle.model,
                vehicle.year,
                vehicle.vin,
                vehicle.reg_number
            ])
        
        put_table(vehicles_table)
        put_button("Назад", onclick=lambda: list_clients())
        return
    
    confirmation = actions("Вы уверены, что хотите удалить клиента?", 
                         ["Да, удалить", "Отменить"])
    
    if confirmation == "Да, удалить":
        with app.app_context():
            try:
                db.session.delete(client)
                db.session.commit()
                clear()
                put_success(f"Клиент {client.full_name} успешно удален")
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при удалении клиента: {str(e)}")
    
    list_clients()

def add_vehicle():
    with app.app_context():
        clients = Client.query.all()
        if not clients:
            put_error("Сначала добавьте клиента")
            return
        
        client_choices = [(str(c.id), f"{c.full_name} ({c.passport})") for c in clients]
    
    while True:
        current_year = datetime.now().year
        info = input_group("Добавление транспортного средства", [
            select("Владелец", name="client_id", options=client_choices, required=True),
            input("Марка", name="brand", required=True),
            input("Модель", name="model", required=True),
            input("Год выпуска", name="year", type=NUMBER, required=True, 
                  help_text=f"от 1900 до {current_year}",
                  validate=lambda y: 1900 <= y <= current_year),
            input("VIN", name="vin", required=True, help_text="17 символов"),
            input("Гос. номер", name="reg_number", required=True),
            input("Мощность двигателя (л.с.)", name="engine_power", type=NUMBER, required=True,
                  help_text="Больше 0", validate=lambda p: p > 0)
        ])
        
        # Валидация данных
        errors = []
        vin_error = validate_vin(info['vin'])
        if vin_error:
            errors.append(vin_error)
            
        reg_number_error = validate_reg_number(info['reg_number'])
        if reg_number_error:
            errors.append(reg_number_error)
            
        if errors:
            clear()
            for error in errors:
                put_error(error)
            continue  # Повторяем ввод данных
        
        with app.app_context():
            # Проверяем, что client_id - это числовая строка перед преобразованием
            try:
                info['client_id'] = int(info['client_id'])
            except ValueError:
                # Если выбранное значение не является числом, найдем клиента по имени
                selected_value = info['client_id']
                for client in clients:
                    if f"{client.full_name} ({client.passport})" == selected_value:
                        info['client_id'] = client.id
                        break
                else:
                    # Если клиент не найден, показать ошибку
                    clear()
                    put_error("Ошибка: невозможно определить ID клиента")
                    continue
            
            # Проверка на существование VIN и регистрационного номера в базе данных
            existing_vin = Vehicle.query.filter_by(vin=info['vin']).first()
            if existing_vin:
                clear()
                put_error(f"Транспортное средство с VIN {info['vin']} уже существует")
                continue
                
            existing_reg = Vehicle.query.filter_by(reg_number=info['reg_number']).first()
            if existing_reg:
                clear()
                put_error(f"Транспортное средство с гос. номером {info['reg_number']} уже существует")
                continue
                
            try:
                vehicle = Vehicle(**info)
                db.session.add(vehicle)
                db.session.commit()
                clear()
                put_success(f"Транспортное средство {info['brand']} {info['model']} успешно добавлено")
                break  # Выход из цикла
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при добавлении ТС: {str(e)}")
                continue
    
    main_menu(_thread_locals.username)

def list_vehicles():
    with app.app_context():
        # Используем joined load для загрузки связанных данных клиента
        vehicles = Vehicle.query.join(Vehicle.client).add_entity(Client).all()
    
    if not vehicles:
        put_warning("Список транспортных средств пуст")
        return
    
    # Добавляем поле поиска
    search_term = input("Поиск по марке, модели, VIN или гос. номеру:", 
                       placeholder="Введите данные для поиска")
    
    filtered_vehicles = vehicles
    if search_term:
        # Фильтруем список ТС
        search_term = search_term.lower()
        filtered_vehicles = [(v, c) for v, c in vehicles if 
                            search_term in v.brand.lower() or
                            search_term in v.model.lower() or
                            search_term in v.vin.lower() or
                            search_term in v.reg_number.lower()]
        
    if not filtered_vehicles:
        put_warning("Транспортные средства не найдены")
        put_button("Назад", onclick=go_to_main_menu)
        return
    
    table = [['ID', 'Владелец', 'Марка', 'Модель', 'Год', 'Гос. номер', 'Действия']]
    for vehicle, client in filtered_vehicles:
        table.append([
            vehicle.id,
            client.full_name,
            vehicle.brand,
            vehicle.model,
            vehicle.year,
            vehicle.reg_number,
            put_buttons(['Оформить ОСАГО', 'Редактировать', 'Удалить'], 
                      [lambda v_id=vehicle.id: create_policy_for_vehicle(v_id),
                       lambda v_id=vehicle.id: edit_vehicle(v_id),
                       lambda v_id=vehicle.id: delete_vehicle(v_id)])
        ])
    
    put_table(table)
    put_button("Назад", onclick=go_to_main_menu)

def edit_vehicle(vehicle_id):
    """Редактирование информации о транспортном средстве"""
    with app.app_context():
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            put_error("Транспортное средство не найдено")
            return
        
        # Получаем список всех клиентов для выбора владельца
        clients = Client.query.all()
        client_choices = [(str(c.id), f"{c.full_name} ({c.passport})") for c in clients]
        
        # Находим текущего владельца для установки значения по умолчанию
        current_client = db.session.get(Client, vehicle.client_id)
    
    clear()
    put_markdown(f"# Редактирование транспортного средства")
    put_markdown(f"Марка: {vehicle.brand}, Модель: {vehicle.model}, Гос. номер: {vehicle.reg_number}")
    
    while True:
        current_year = datetime.now().year
        info = input_group("Редактирование транспортного средства", [
            select("Владелец", name="client_id", options=client_choices, value=str(vehicle.client_id), required=True),
            input("Марка", name="brand", value=vehicle.brand, required=True),
            input("Модель", name="model", value=vehicle.model, required=True),
            input("Год выпуска", name="year", type=NUMBER, value=vehicle.year, required=True, 
                  help_text=f"от 1900 до {current_year}",
                  validate=lambda y: 1900 <= y <= current_year),
            input("VIN", name="vin", value=vehicle.vin, required=True, help_text="17 символов"),
            input("Гос. номер", name="reg_number", value=vehicle.reg_number, required=True),
            input("Мощность двигателя (л.с.)", name="engine_power", type=NUMBER, value=vehicle.engine_power, required=True,
                  help_text="Больше 0", validate=lambda p: p > 0)
        ])
        
        # Валидация данных
        errors = []
        vin_error = validate_vin(info['vin'])
        if vin_error:
            errors.append(vin_error)
            
        reg_number_error = validate_reg_number(info['reg_number'])
        if reg_number_error:
            errors.append(reg_number_error)
            
        if errors:
            clear()
            for error in errors:
                put_error(error)
            continue  # Повторяем ввод данных
        
        with app.app_context():
            # Проверяем, что client_id - это числовая строка перед преобразованием
            try:
                info['client_id'] = int(info['client_id'])
            except ValueError:
                # Если выбранное значение не является числом, найдем клиента по имени
                selected_value = info['client_id']
                for client in clients:
                    if f"{client.full_name} ({client.passport})" == selected_value:
                        info['client_id'] = client.id
                        break
                else:
                    # Если клиент не найден, показать ошибку
                    clear()
                    put_error("Ошибка: невозможно определить ID клиента")
                    continue
            
            # Проверка на существование VIN и регистрационного номера в базе данных (у других ТС)
            existing_vin = Vehicle.query.filter(
                Vehicle.vin == info['vin'], 
                Vehicle.id != vehicle_id
            ).first()
            
            if existing_vin:
                clear()
                put_error(f"Транспортное средство с VIN {info['vin']} уже существует")
                continue
                
            existing_reg = Vehicle.query.filter(
                Vehicle.reg_number == info['reg_number'], 
                Vehicle.id != vehicle_id
            ).first()
            
            if existing_reg:
                clear()
                put_error(f"Транспортное средство с гос. номером {info['reg_number']} уже существует")
                continue
                
            try:
                vehicle.client_id = info['client_id']
                vehicle.brand = info['brand']
                vehicle.model = info['model']
                vehicle.year = info['year']
                vehicle.vin = info['vin']
                vehicle.reg_number = info['reg_number']
                vehicle.engine_power = info['engine_power']
                
                db.session.commit()
                clear()
                put_success(f"Транспортное средство {info['brand']} {info['model']} успешно обновлено")
                break  # Выход из цикла
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при обновлении ТС: {str(e)}")
                continue
    
    list_vehicles()

def delete_vehicle(vehicle_id):
    """Удаление транспортного средства из базы данных"""
    with app.app_context():
        vehicle = db.session.get(Vehicle, vehicle_id)
        if not vehicle:
            put_error("Транспортное средство не найдено")
            return
        
        client = db.session.get(Client, vehicle.client_id)
        
        # Проверяем наличие полисов для этого ТС
        policies = Policy.query.filter_by(vehicle_id=vehicle_id).all()
    
    clear()
    put_markdown(f"# Удаление транспортного средства")
    put_table([
        ['Марка', vehicle.brand],
        ['Модель', vehicle.model],
        ['Год', vehicle.year],
        ['VIN', vehicle.vin],
        ['Гос. номер', vehicle.reg_number],
        ['Владелец', client.full_name if client else 'Не указан']
    ])
    
    if policies:
        put_error("Невозможно удалить транспортное средство, так как для него оформлены полисы ОСАГО.")
        put_markdown("Перед удалением необходимо удалить все связанные полисы.")
        
        policies_table = [['ID', 'Номер полиса', 'Дата начала', 'Дата окончания', 'Стоимость', 'Статус']]
        for policy in policies:
            status = "Отменен" if policy.status == 'cancelled' else "Активен"
            policies_table.append([
                policy.id,
                policy.number,
                policy.start_date.strftime('%d.%m.%Y'),
                policy.end_date.strftime('%d.%m.%Y'),
                f"{policy.cost} руб.",
                status
            ])
        
        put_table(policies_table)
        put_button("Назад", onclick=lambda: list_vehicles())
        return
    
    confirmation = actions("Вы уверены, что хотите удалить транспортное средство?", 
                         ["Да, удалить", "Отменить"])
    
    if confirmation == "Да, удалить":
        with app.app_context():
            try:
                db.session.delete(vehicle)
                db.session.commit()
                clear()
                put_success(f"Транспортное средство {vehicle.brand} {vehicle.model} успешно удалено")
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при удалении транспортного средства: {str(e)}")
    
    list_vehicles()

def list_vehicles_for_policy():
    """Отображает список транспортных средств для оформления полиса"""
    with app.app_context():
        # Используем joined load для загрузки связанных данных клиента
        vehicles = Vehicle.query.join(Vehicle.client).add_entity(Client).all()
    
    if not vehicles:
        put_warning("Список транспортных средств пуст")
        return
    
    put_markdown("## Выберите транспортное средство для оформления полиса ОСАГО")
    
    table = [['ID', 'Владелец', 'Марка', 'Модель', 'Год', 'Гос. номер', 'Действия']]
    for vehicle, client in vehicles:
        table.append([
            vehicle.id,
            client.full_name,
            vehicle.brand,
            vehicle.model,
            vehicle.year,
            vehicle.reg_number,
            put_buttons(['Оформить ОСАГО'], 
                      lambda v_id=vehicle.id: create_policy_for_vehicle(v_id))
        ])
    
    put_table(table)
    put_button("Назад", onclick=lambda: main_menu(_thread_locals.username))

def calculate_policy_cost(vehicle, period_months=12, driver_experience=0, driver_age=30, bonus_malus=1.0):
    """
    Расчет стоимости полиса ОСАГО с учетом дополнительных факторов:
    - Мощность двигателя
    - Возраст транспортного средства
    - Стаж вождения водителя
    - Возраст водителя
    - Коэффициент бонус-малус (скидка за безаварийную езду)
    - Срок действия полиса
    """
    base_rate = 5000  # Базовый тариф
    
    # Коэффициент мощности двигателя
    if vehicle.engine_power <= 50:
        power_ratio = 0.6
    elif vehicle.engine_power <= 100:
        power_ratio = 1.0
    elif vehicle.engine_power <= 150:
        power_ratio = 1.4
    elif vehicle.engine_power <= 200:
        power_ratio = 1.8
    else:
        power_ratio = 2.2
    
    # Коэффициент возраста ТС
    vehicle_age = datetime.now().year - vehicle.year
    if vehicle_age <= 3:
        age_ratio = 1.0
    elif vehicle_age <= 7:
        age_ratio = 1.1
    elif vehicle_age <= 10:
        age_ratio = 1.3
    else:
        age_ratio = 1.5
    
    # Коэффициент стажа вождения
    if driver_experience <= 3:
        experience_ratio = 1.3
    elif driver_experience <= 5:
        experience_ratio = 1.1
    elif driver_experience <= 10:
        experience_ratio = 0.9
    else:
        experience_ratio = 0.8
    
    # Коэффициент возраста водителя
    if driver_age < 22:
        driver_age_ratio = 1.7
    elif driver_age < 25:
        driver_age_ratio = 1.3
    elif driver_age < 60:
        driver_age_ratio = 1.0
    else:
        driver_age_ratio = 1.2
    
    # Учет всех коэффициентов
    total_cost = (base_rate * power_ratio * age_ratio * experience_ratio 
                * driver_age_ratio * bonus_malus * (period_months / 12))
    
    return round(total_cost, 2)

def create_policy_for_vehicle(vehicle_id):
    try:
        # Попытка преобразовать vehicle_id в целое число, если он передан как строка
        vehicle_id = int(vehicle_id) if not isinstance(vehicle_id, int) else vehicle_id
        
        with app.app_context():
            vehicle = Vehicle.query.join(Vehicle.client).filter(Vehicle.id == vehicle_id).first()
        
        if not vehicle:
            put_error("Транспортное средство не найдено")
            return
    except (ValueError, TypeError):
        put_error("Некорректный ID транспортного средства")
        return
    
    period_choices = [
        ('3', '3 месяца'),
        ('6', '6 месяцев'),
        ('12', '12 месяцев')
    ]
    
    bonus_malus_choices = [
        ('0.5', 'Класс M (50% скидка)'),
        ('0.65', 'Класс 13-14 (35% скидка)'),
        ('0.8', 'Класс 10-12 (20% скидка)'),
        ('0.9', 'Класс 7-9 (10% скидка)'),
        ('1.0', 'Класс 3-6 (нет скидки/надбавки)'),
        ('1.4', 'Класс 2-1 (40% надбавка)'),
        ('1.6', 'Класс 0,-1,-2 (60% надбавка)'),
        ('2.45', 'Класс M (145% надбавка)')
    ]
    
    # Собираем данные для расчета полиса
    info = input_group("Оформление полиса ОСАГО", [
        select("Срок действия", name="period", options=period_choices, required=True),
        input("Возраст водителя", name="driver_age", type=NUMBER, required=True,
              value=30, validate=lambda a: 18 <= a <= 99),
        input("Стаж вождения (лет)", name="driver_experience", type=NUMBER, required=True,
              value=5, validate=lambda e: 0 <= e <= 60),
        select("Коэффициент бонус-малус", name="bonus_malus", options=bonus_malus_choices, required=True)
    ])
    
    try:
        period_months = int(info['period'])
    except ValueError:
        # Если выбранное значение не является числом, определяем по описанию
        if '3 месяца' in info['period']:
            period_months = 3
        elif '6 месяцев' in info['period']:
            period_months = 6
        elif '12 месяцев' in info['period']:
            period_months = 12
        else:
            period_months = 12  # По умолчанию 12 месяцев
            
    # Получаем остальные параметры
    driver_age = int(info['driver_age'])
    driver_experience = int(info['driver_experience'])
    bonus_malus = float(info['bonus_malus'])
    
    # Проверка корректности данных о стаже и возрасте
    if driver_experience > (driver_age - 18):
        clear()
        put_error(f"Стаж вождения не может быть больше, чем (возраст водителя - 18)")
        put_button("Назад", onclick=lambda v_id=vehicle_id: create_policy_for_vehicle(v_id))
        return
    
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30*period_months)
    
    # Расчитываем стоимость с учетом всех параметров
    cost = calculate_policy_cost(vehicle, period_months, driver_experience, driver_age, bonus_malus)
    
    # Генерация номера полиса (улучшенная версия)
    prefix = "OSG"
    date_part = datetime.now().strftime('%Y%m%d')
    random_part = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    policy_number = f"{prefix}-{date_part}-{random_part}"
    
    with app.app_context():
        policy = Policy(
            number=policy_number,
            vehicle_id=vehicle.id,
            start_date=start_date,
            end_date=end_date,
            cost=cost
        )
        
        db.session.add(policy)
        db.session.commit()
    
    clear()
    put_success(f"Полис ОСАГО успешно оформлен")
    put_markdown("## Информация о полисе")
    put_table([
        ['Номер полиса', policy_number],
        ['Транспортное средство', f"{vehicle.brand} {vehicle.model}"],
        ['Владелец', vehicle.client.full_name],
        ['Срок действия', f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"],
        ['Возраст водителя', f"{driver_age} лет"],
        ['Стаж вождения', f"{driver_experience} лет"],
        ['Класс КБМ', next((desc for val, desc in bonus_malus_choices if val == info['bonus_malus']), '-')],
        ['Стоимость', f"{cost} руб."]
    ])
    
    # Добавляем PDF-генерацию
    put_markdown("## Действия с полисом")
    put_buttons(['Скачать полис PDF', 'Отправить на email'], 
               [lambda: generate_policy_pdf(policy.id), 
                lambda: send_policy_by_email(policy.id, vehicle.client)])
    put_button("В главное меню", onclick=lambda: main_menu(_thread_locals.username))

def generate_policy_pdf(policy_id):
    """Генерация PDF для страхового полиса"""
    try:
        from fpdf import FPDF
        import tempfile
        import os
        
        with app.app_context():
            result = (Policy.query
                     .filter(Policy.id == policy_id)
                     .join(Policy.vehicle)
                     .join(Vehicle.client)
                     .add_entity(Vehicle)
                     .add_entity(Client)
                     .first())
        
        if not result:
            put_error("Полис не найден")
            return None
            
        policy, vehicle, client = result
          # Создаем PDF документ с поддержкой кириллицы
        pdf = FPDF()
        # Добавляем кириллический шрифт (обычный и полужирный)
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'arial.ttf')
        pdf.add_font('CustomFont', '', font_path)
        pdf.add_font('CustomFont', 'B', font_path)
        pdf.add_page()
        
        # Используем шрифт с поддержкой кириллицы
        pdf.set_font("CustomFont", "", 16)
        pdf.cell(0, 10, "СТРАХОВОЙ ПОЛИС ОСАГО", 0, 1, 'C')
        pdf.ln(10)
          # Информация о полисе
        pdf.set_font("CustomFont", "B", 12)
        pdf.cell(0, 10, f"Полис №: {policy.number}", 0, 1)
        pdf.cell(0, 10, f"Дата оформления: {policy.created_at.strftime('%d.%m.%Y')}", 0, 1)
        pdf.cell(0, 10, f"Срок действия: {policy.start_date.strftime('%d.%m.%Y')} - {policy.end_date.strftime('%d.%m.%Y')}", 0, 1)
        pdf.cell(0, 10, f"Стоимость: {policy.cost} руб.", 0, 1)
        pdf.ln(5)
        
        # Информация о ТС
        pdf.set_font("CustomFont", "B", 14)
        pdf.cell(0, 10, "Информация о транспортном средстве:", 0, 1)
        pdf.set_font("CustomFont", "", 12)
        pdf.cell(0, 10, f"Марка и модель: {vehicle.brand} {vehicle.model}", 0, 1)
        pdf.cell(0, 10, f"Год выпуска: {vehicle.year}", 0, 1)
        pdf.cell(0, 10, f"VIN: {vehicle.vin}", 0, 1)
        pdf.cell(0, 10, f"Гос. номер: {vehicle.reg_number}", 0, 1)
        pdf.ln(5)
        
        # Информация о владельце
        pdf.set_font("CustomFont", "B", 14)
        pdf.cell(0, 10, "Информация о владельце:", 0, 1)
        pdf.set_font("CustomFont", "", 12)
        pdf.cell(0, 10, f"ФИО: {client.full_name}", 0, 1)
        pdf.cell(0, 10, f"Паспорт: {client.passport}", 0, 1)
        if client.phone:
            pdf.cell(0, 10, f"Телефон: {client.phone}", 0, 1)
        if client.email:
            pdf.cell(0, 10, f"Email: {client.email}", 0, 1)
        
        # Подпись
        pdf.ln(20)
        pdf.cell(80, 10, "Подпись страховщика: _________________", 0, 1)
        pdf.cell(80, 10, "Подпись страхователя: _________________", 0, 1)
          # Создаем файл в папке для загрузок
        file_name = f"policy_{policy.number}.pdf"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        
        try:
            # Сохраняем PDF в файл
            pdf.output(file_path)
            put_success(f"PDF полиса успешно создан")
              # Создаем ссылку для скачивания прямо из статической директории
            filename = f"policy_{policy.number}.pdf"
            download_url = f"/download/files/{filename}"
            put_markdown(f"[Скачать полис {policy.number}.pdf]({download_url})")
            return file_path
            
        except Exception as e:
            put_error(f"Ошибка при создании PDF: {str(e)}")
            return None
        
    except ImportError:
        put_error("Для создания PDF требуется установить библиотеку fpdf2.")
        put_markdown("Выполните команду: `pip install fpdf2`")
        return None

def send_policy_by_email(policy_id, client):
    """Имитация отправки полиса по электронной почте"""
    clear()
    
    if not client.email:
        put_error("У клиента не указан адрес электронной почты")
        put_button("Назад", onclick=lambda: show_policy_details(policy_id))
        return
    
    # Генерируем PDF для отправки
    pdf_path = generate_policy_pdf(policy_id)
    
    if not pdf_path:
        put_error("Не удалось создать PDF для отправки")
        put_button("Назад", onclick=lambda: show_policy_details(policy_id))
        return
    
    put_markdown("## Отправка полиса по электронной почте")
    
    # Имитация отправки email
    put_success(f"Полис успешно отправлен на адрес {client.email}")
    put_button("Назад", onclick=lambda: show_policy_details(policy_id))

def cancel_policy(policy_id):
    """Отмена полиса ОСАГО"""
    with app.app_context():
        policy = db.session.get(Policy, policy_id)
        if not policy:
            put_error("Полис не найден")
            return
        
        # Получаем данные о транспортном средстве и клиенте для отображения
        vehicle = db.session.get(Vehicle, policy.vehicle_id)
        client = db.session.get(Client, vehicle.client_id) if vehicle else None
        
        if not vehicle or not client:
            put_error("Ошибка при получении данных о транспортном средстве или клиенте")
            return
    
    clear()
    put_markdown(f"# Отмена полиса ОСАГО {policy.number}")
    
    put_table([
        ['Номер полиса', policy.number],
        ['Транспортное средство', f"{vehicle.brand} {vehicle.model}"],
        ['Владелец', client.full_name],
        ['Срок действия', f"с {policy.start_date.strftime('%d.%m.%Y')} по {policy.end_date.strftime('%d.%m.%Y')}"],
        ['Стоимость', f"{policy.cost} руб."]
    ])
    
    # Запрос причины отмены
    reason = textarea("Укажите причину отмены полиса:", rows=3, required=True)
    
    # Запрос подтверждения
    confirmation = actions("Вы уверены, что хотите отменить полис?", 
                         ["Да, отменить", "Нет, вернуться назад"])
    
    if confirmation == "Да, отменить":
        with app.app_context():
            try:
                policy.status = 'cancelled'
                policy.notes = reason  # Добавляем причину отмены в примечания
                db.session.commit()
                clear()
                put_success("Полис успешно отменен")
            except Exception as e:
                db.session.rollback()
                clear()
                put_error(f"Ошибка при отмене полиса: {str(e)}")
                return
        
        # После успешной отмены показываем подробности полиса
        show_policy_details(policy_id)
    else:
        # Если пользователь отменил действие, возвращаемся к деталям полиса
        show_policy_details(policy_id)

def list_policies():
    """Отображение списка полисов со статистикой и фильтрами"""
    # Статистика по полисам
    with app.app_context():
        current_date = datetime.now()
        
        total_policies = Policy.query.count()
        active_policies = Policy.query.filter_by(status='active').count()
        cancelled_policies = Policy.query.filter_by(status='cancelled').count()
        
        # Полисы с истекшим сроком действия
        expired_policies = Policy.query.filter(
            Policy.status == 'active', 
            Policy.end_date < current_date
        ).count()
        
        # Общая сумма всех активных полисов
        sum_active = db.session.query(db.func.sum(Policy.cost)).filter_by(status='active').scalar() or 0
        
        # Полисы, срок действия которых заканчивается в ближайшие 30 дней
        expiring_soon = Policy.query.filter(
            Policy.status == 'active',
            Policy.end_date > current_date,
            Policy.end_date < (current_date + timedelta(days=30))
        ).count()
    
    clear()
    put_markdown("# Управление полисами ОСАГО")
    
    # Отображаем статистику
    put_markdown("## Статистика по полисам")
    stats_table = [
        ['Всего полисов', total_policies],
        ['Активные', active_policies],
        ['Отмененные', cancelled_policies],
        ['Истекшие', expired_policies],
        ['Истекают в ближайшие 30 дней', expiring_soon],
        ['Общая сумма активных полисов', f"{round(sum_active, 2)} руб."]
    ]
    put_table(stats_table)
    
    with app.app_context():
        # Получаем все полисы с данными клиентов и ТС
        results = (Policy.query
                  .join(Policy.vehicle)
                  .join(Vehicle.client)
                  .add_entity(Vehicle)
                  .add_entity(Client)
                  .all())
    
    if not results:
        put_warning("Список полисов пуст")
        put_button("В главное меню", onclick=lambda: main_menu(_thread_locals.username))
        return
    
    # Добавляем фильтры
    put_markdown("## Фильтры")
    
    status_filter = select("Статус полиса:", options=[
        ('all', 'Все'),
        ('active', 'Только активные'),
        ('cancelled', 'Отмененные'),
        ('expired', 'Истекшие'),
        ('expiring_soon', 'Истекают в ближайшие 30 дней')
    ], value='all')
    
    # Добавляем поиск
    search_term = input("Поиск по номеру полиса, владельцу или ТС:", 
                       placeholder="Введите данные для поиска")
    
    # Применяем фильтрацию
    filtered_results = results
    
    # Фильтр по статусу
    if status_filter == 'active':
        filtered_results = [(p, v, c) for p, v, c in results 
                           if p.status == 'active' and p.end_date >= current_date]
    elif status_filter == 'cancelled':
        filtered_results = [(p, v, c) for p, v, c in results 
                           if p.status == 'cancelled']
    elif status_filter == 'expired':
        filtered_results = [(p, v, c) for p, v, c in results 
                           if p.status == 'active' and p.end_date < current_date]
    elif status_filter == 'expiring_soon':
        filtered_results = [(p, v, c) for p, v, c in results 
                           if p.status == 'active' and p.end_date > current_date 
                           and p.end_date < (current_date + timedelta(days=30))]
    
    # Поиск по строке
    if search_term:
        search_term = search_term.lower()
        filtered_results = [(p, v, c) for p, v, c in filtered_results if 
                           search_term in p.number.lower() or
                           search_term in c.full_name.lower() or
                           search_term in v.brand.lower() or
                           search_term in v.model.lower() or
                           search_term in v.reg_number.lower()]
    
    if not filtered_results:
        put_warning("Полисы по заданным критериям не найдены")
        put_button("Сбросить фильтры", onclick=lambda: list_policies())
        return
    
    # Отображаем список полисов
    put_markdown("## Список полисов")
    table = [['Номер полиса', 'Владелец', 'Транспортное средство', 'Срок действия', 'Стоимость', 'Статус', 'Действия']]
    
    for policy, vehicle, client in filtered_results:
        # Определяем актуальный статус
        if current_date > policy.end_date and policy.status == 'active':
            actual_status = "Истек"
        elif policy.status == 'cancelled':
            actual_status = "Отменен"
        else:
            actual_status = "Активен"
            
        table.append([
            policy.number,
            client.full_name,
            f"{vehicle.brand} {vehicle.model}",
            f"{policy.start_date.strftime('%d.%m.%Y')} - {policy.end_date.strftime('%d.%m.%Y')}",
            f"{policy.cost} руб.",
            actual_status,
            put_buttons(['Подробнее'], lambda p_id=policy.id: show_policy_details(p_id))
        ])
    
    put_table(table)
    put_button("В главное меню", onclick=lambda: main_menu(_thread_locals.username))

def show_policy_details(policy_id):
    """Просмотр детальной информации о полисе и управление им"""
    with app.app_context():
        result = (Policy.query
                 .filter(Policy.id == policy_id)
                 .join(Policy.vehicle)
                 .join(Vehicle.client)
                 .add_entity(Vehicle)
                 .add_entity(Client)
                 .first())
    
    if not result:
        put_error("Полис не найден")
        return
        
    policy, vehicle, client = result
    
    clear()
    put_markdown(f"# Информация о полисе {policy.number}")
    
    # Определяем статус полиса (действующий, истекший)
    current_date = datetime.now()
    if current_date > policy.end_date:
        actual_status = "Истек"
    elif policy.status == 'cancelled':
        actual_status = "Отменен"
    else:
        actual_status = "Действующий"
    
    # Если полис отменен, показываем причину отмены
    if policy.status == 'cancelled' and policy.notes:
        put_markdown("## Причина отмены")
        put_text(policy.notes)
    
    # Отображаем кнопки действий в зависимости от статуса полиса
    put_markdown("## Действия с полисом")
    
    if actual_status == "Действующий":
        put_buttons(['Отменить полис', 'Скачать PDF', 'Отправить на Email'], 
                  [lambda p_id=policy_id: cancel_policy(p_id), 
                   lambda p_id=policy_id: generate_policy_pdf(p_id),
                   lambda: send_policy_by_email(policy_id, client)])
    elif actual_status == "Истек":
        put_buttons(['Оформить новый полис', 'Скачать PDF'],
                  [lambda v_id=vehicle.id: create_policy_for_vehicle(v_id),
                   lambda p_id=policy_id: generate_policy_pdf(p_id)])
    else:  # Отмененный полис
        put_buttons(['Скачать PDF'],
                  [lambda p_id=policy_id: generate_policy_pdf(p_id)])
    
    put_button("Назад", onclick=lambda: list_policies())

def check_expiring_policies():
    """
    Функция для проверки истекающих полисов и отправки уведомлений
    """
    clear()
    put_markdown("# Уведомления о полисах")
    
    with app.app_context():
        current_date = datetime.now()
        
        # Полисы, срок действия которых заканчивается в ближайшие 30 дней
        expiring_policies = (Policy.query
                            .filter(Policy.status == 'active')
                            .filter(Policy.end_date > current_date)
                            .filter(Policy.end_date < (current_date + timedelta(days=30)))
                            .join(Policy.vehicle)
                            .join(Vehicle.client)
                            .add_entity(Vehicle)
                            .add_entity(Client)
                            .all())
        
        # Просроченные полисы (истекшие, но активные)
        expired_policies = (Policy.query
                           .filter(Policy.status == 'active')
                           .filter(Policy.end_date < current_date)
                           .join(Policy.vehicle)
                           .join(Vehicle.client)
                           .add_entity(Vehicle)
                           .add_entity(Client)
                           .all())
    
    # Отображение истекающих полисов
    put_markdown("## Полисы, истекающие в ближайшие 30 дней")
    
    if expiring_policies:
        table = [['Номер полиса', 'Владелец', 'ТС', 'Срок окончания', 'Дней до окончания', 'Контакты', 'Действия']]
        
        for policy, vehicle, client in expiring_policies:
            days_left = (policy.end_date - current_date).days
            contacts = []
            if client.phone:
                contacts.append(f"Тел: {client.phone}")
            if client.email:
                contacts.append(f"Email: {client.email}")
                
            table.append([
                policy.number,
                client.full_name,
                f"{vehicle.brand} {vehicle.model} ({vehicle.reg_number})",
                policy.end_date.strftime('%d.%m.%Y'),
                days_left,
                ', '.join(contacts) if contacts else 'Нет контактов',
                put_buttons(['Уведомить', 'Подробнее'], 
                          [lambda p=policy, c=client, v=vehicle: send_expiry_notification(p, c, v), 
                           lambda p_id=policy.id: show_policy_details(p_id)])
            ])
            
        put_table(table)
    else:
        put_warning("Нет полисов, истекающих в ближайшие 30 дней")
    
    # Отображение просроченных полисов
    put_markdown("## Просроченные полисы")
    
    if expired_policies:
        table = [['Номер полиса', 'Владелец', 'ТС', 'Срок окончания', 'Просрочен (дней)', 'Действия']]
        
        for policy, vehicle, client in expired_policies:
            days_overdue = (current_date - policy.end_date).days
            
            table.append([
                policy.number,
                client.full_name,
                f"{vehicle.brand} {vehicle.model} ({vehicle.reg_number})",
                policy.end_date.strftime('%d.%m.%Y'),
                days_overdue,
                put_buttons(['Оформить новый', 'Подробнее'], 
                          [lambda v_id=vehicle.id: create_policy_for_vehicle(v_id),
                           lambda p_id=policy.id: show_policy_details(p_id)])
            ])
            
        put_table(table)
    else:
        put_warning("Нет просроченных полисов")
    
    put_buttons(['Отправить массовые уведомления', 'В главное меню'], 
              [send_mass_notifications, lambda: main_menu(_thread_locals.username)])

def send_expiry_notification(policy, client, vehicle):
    """
    Функция для отправки уведомления об истекающем полисе
    """
    clear()
    put_markdown(f"# Отправка уведомления о полисе {policy.number}")
    
    if not client.email and not client.phone:
        put_error("У клиента не указаны контактные данные (email или телефон)")
        put_button("Назад", onclick=lambda: check_expiring_policies())
        return
    
    # Подготовка данных для уведомления
    current_date = datetime.now()
    days_left = (policy.end_date - current_date).days
    
    notification_methods = []
    if client.email:
        notification_methods.append(('email', f'По электронной почте ({client.email})'))
    if client.phone:
        notification_methods.append(('sms', f'По SMS ({client.phone})'))
    notification_methods.append(('preview', 'Просмотр шаблона уведомления'))
    
    method = select("Выберите способ отправки уведомления:", options=notification_methods)
    
    if method == 'email':
        try:
            # Здесь будет код для отправки email с использованием flask-mail
            # В данной реализации покажем шаблон уведомления
            
            # Подготовка HTML шаблона
            import os
            template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'notification_template.html')
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = f.read()
                    
                # Заполнение данных шаблона
                email_html = template.replace('{{client_name}}', client.full_name)
                email_html = email_html.replace('{{policy_number}}', policy.number)
                email_html = email_html.replace('{{expiry_date}}', policy.end_date.strftime('%d.%m.%Y'))
                email_html = email_html.replace('{{days_left}}', str(days_left))
                email_html = email_html.replace('{{vehicle_name}}', f"{vehicle.brand} {vehicle.model}")
                email_html = email_html.replace('{{reg_number}}', vehicle.reg_number)
                email_html = email_html.replace('{{start_date}}', policy.start_date.strftime('%d.%m.%Y'))
                email_html = email_html.replace('{{end_date}}', policy.end_date.strftime('%d.%m.%Y'))
                
                put_success(f"Уведомление успешно отправлено на адрес {client.email}")
                put_markdown("## Предварительный просмотр отправленного уведомления:")
                put_html(email_html)
            else:
                put_error("Шаблон уведомления не найден")
                put_warning(f"Имитация отправки email на адрес {client.email}")
                put_success("Уведомление об истечении срока действия полиса успешно отправлено")
                
        except Exception as e:
            put_error(f"Ошибка при отправке уведомления: {str(e)}")
    
    elif method == 'sms':
        # Имитация отправки SMS
        put_success(f"SMS-уведомление успешно отправлено на номер {client.phone}")
        put_markdown(f"""
## Текст SMS:
Уважаемый(ая) {client.full_name}, срок действия Вашего полиса ОСАГО {policy.number} заканчивается {policy.end_date.strftime('%d.%m.%Y')} (через {days_left} дн.). Для оформления нового полиса обратитесь в нашу компанию.
        """)
    
    elif method == 'preview':
        # Подготовка HTML шаблона
        import os
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'notification_template.html')
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
                
            # Заполнение данных шаблона
            email_html = template.replace('{{client_name}}', client.full_name)
            email_html = email_html.replace('{{policy_number}}', policy.number)
            email_html = email_html.replace('{{expiry_date}}', policy.end_date.strftime('%d.%m.%Y'))
            email_html = email_html.replace('{{days_left}}', str(days_left))
            email_html = email_html.replace('{{vehicle_name}}', f"{vehicle.brand} {vehicle.model}")
            email_html = email_html.replace('{{reg_number}}', vehicle.reg_number)
            email_html = email_html.replace('{{start_date}}', policy.start_date.strftime('%d.%m.%Y'))
            email_html = email_html.replace('{{end_date}}', policy.end_date.strftime('%d.%m.%Y'))
            
            put_markdown("## Предварительный просмотр уведомления:")
            put_html(email_html)
        else:
            put_error("Шаблон уведомления не найден")
            put_markdown(f"""
## Предварительный просмотр уведомления:

# Уведомление о полисе ОСАГО

Уважаемый(ая) {client.full_name},

Информируем Вас о том, что срок действия Вашего полиса ОСАГО {policy.number} 
заканчивается {policy.end_date.strftime('%d.%m.%Y')} (через {days_left} дней).

Для обеспечения непрерывной страховой защиты рекомендуем своевременно оформить новый полис.

**Данные полиса:**
- Номер полиса: {policy.number}
- Транспортное средство: {vehicle.brand} {vehicle.model}
- Гос. номер: {vehicle.reg_number}
- Срок действия: с {policy.start_date.strftime('%d.%m.%Y')} по {policy.end_date.strftime('%d.%m.%Y')}

С уважением,
Страховая компания ОСАГО
            """)
    
    put_button("Назад", onclick=lambda: check_expiring_policies())

def send_mass_notifications():
    """
    Функция для массовой отправки уведомлений об истекающих полисах
    """
    clear()
    put_markdown("# Массовая отправка уведомлений")
    
    with app.app_context():
        current_date = datetime.now()
        
        # Полисы, срок действия которых заканчивается в ближайшие 30 дней
        expiring_policies = (Policy.query
                            .filter(Policy.status == 'active')
                            .filter(Policy.end_date > current_date)
                            .filter(Policy.end_date < (current_date + timedelta(days=30)))
                            .join(Policy.vehicle)
                            .join(Vehicle.client)
                            .add_entity(Vehicle)
                            .add_entity(Client)
                            .all())
    
    if not expiring_policies:
        put_warning("Нет полисов, требующих уведомления")
        put_button("Назад", onclick=lambda: check_expiring_policies())
        return
    
    # Отображаем сводку
    put_markdown("## Сводка для отправки уведомлений")
    put_markdown(f"Всего полисов, истекающих в ближайшие 30 дней: {len(expiring_policies)}")
    
    # Подсчитываем количество клиентов с email и телефоном
    clients_with_email = sum(1 for _, _, client in expiring_policies if client.email)
    clients_with_phone = sum(1 for _, _, client in expiring_policies if client.phone)
    
    put_markdown(f"Клиентов с email: {clients_with_email}")
    put_markdown(f"Клиентов с телефоном: {clients_with_phone}")
    
    # Показываем форму для отправки
    put_markdown("## Выберите параметры отправки")
    
    notification_settings = input_group("Настройки массовой отправки", [
        checkbox("Способы отправки", name="methods", options=[
            {'label': 'Email', 'value': 'email'},
            {'label': 'SMS', 'value': 'sms'}
        ], value=['email']),
        input("Минимальное количество дней до окончания полиса", name="min_days", type=NUMBER, value=1),
        input("Максимальное количество дней до окончания полиса", name="max_days", type=NUMBER, value=30)
    ])
    
    # Фильтруем полисы по параметрам
    filtered_policies = []
    for policy, vehicle, client in expiring_policies:
        days_left = (policy.end_date - current_date).days
        if notification_settings['min_days'] <= days_left <= notification_settings['max_days']:
            can_notify = False
            if 'email' in notification_settings['methods'] and client.email:
                can_notify = True
            if 'sms' in notification_settings['methods'] and client.phone:
                can_notify = True
            
            if can_notify:
                filtered_policies.append((policy, vehicle, client))
    
    if not filtered_policies:
        put_warning("Нет полисов, подходящих под критерии для отправки уведомлений")
        put_button("Назад", onclick=lambda: check_expiring_policies())
        return
    
    # Запрашиваем подтверждение
    put_markdown(f"## Подтверждение отправки {len(filtered_policies)} уведомлений")
    
    confirmation = actions("Подтвердите отправку уведомлений", 
                         ["Отправить", "Отменить"])
    
    if confirmation == "Отправить":
        # Имитация процесса отправки
        import time
        
        put_markdown("## Процесс отправки уведомлений")
        put_processbar('sending', 0, 'Отправка...')
        
        emails_sent = 0
        sms_sent = 0
        
        for i, (policy, vehicle, client) in enumerate(filtered_policies):
            time.sleep(0.1)  # Имитация задержки для наглядности
            set_processbar('sending', (i + 1) / len(filtered_policies))
            
            methods_used = []
            if 'email' in notification_settings['methods'] and client.email:
                # Здесь будет реальная отправка email
                emails_sent += 1
                methods_used.append(f"email: {client.email}")
            
            if 'sms' in notification_settings['methods'] and client.phone:
                # Здесь будет реальная отправка SMS
                sms_sent += 1
                methods_used.append(f"SMS: {client.phone}")
            
            if methods_used:
                put_text(f"Отправлено уведомление клиенту {client.full_name} ({', '.join(methods_used)})")
        
        clear()
        put_markdown("# Результаты отправки уведомлений")
        put_success(f"Отправка завершена. Всего отправлено {emails_sent + sms_sent} уведомлений.")
        put_markdown(f"- По email: {emails_sent}")
        put_markdown(f"- По SMS: {sms_sent}")
    
    put_button("Назад", onclick=lambda: check_expiring_policies())

def show_statistics():
    """
    Отображение статистики по полисам ОСАГО
    """
    clear()
    put_markdown("# Статистика и аналитика")
    
    with app.app_context():
        current_date = datetime.now()
        
        # Общие данные о полисах
        total_policies = Policy.query.count()
        active_policies = Policy.query.filter_by(status='active').filter(Policy.end_date >= current_date).count()
        cancelled_policies = Policy.query.filter_by(status='cancelled').count()
        expired_policies = Policy.query.filter(Policy.status == 'active', Policy.end_date < current_date).count()
        
        # Общая сумма по полисам
        total_sum = db.session.query(db.func.sum(Policy.cost)).scalar() or 0
        active_sum = db.session.query(db.func.sum(Policy.cost)).filter_by(status='active').filter(Policy.end_date >= current_date).scalar() or 0
        
        # Количество полисов по периодам (3, 6, 12 месяцев)
        period_data = {}
        all_policies = Policy.query.all()
        for policy in all_policies:
            days = (policy.end_date - policy.start_date).days
            if days <= 100:  # ~3 месяца
                period = "3 месяца"
            elif days <= 190:  # ~6 месяцев
                period = "6 месяцев"
            else:
                period = "12 месяцев"
            
            period_data[period] = period_data.get(period, 0) + 1
    
    # Отображаем основную статистику
    put_markdown("## Общая статистика по полисам")
    stats_table = [
        ['Всего полисов', total_policies],
        ['Действующие полисы', active_policies],
        ['Отмененные полисы', cancelled_policies],
        ['Истекшие полисы', expired_policies],
        ['Общая сумма всех полисов', f"{round(total_sum, 2)} руб."],
        ['Общая сумма действующих полисов', f"{round(active_sum, 2)} руб."]
    ]
    put_table(stats_table)
    
    # Отображаем статистику по периодам
    put_markdown("## Распределение полисов по срокам")
    period_table = [['Период', 'Количество полисов', 'Процент']]
    for period, count in period_data.items():
        percent = round(count / total_policies * 100, 2) if total_policies > 0 else 0
        period_table.append([period, count, f"{percent}%"])
    put_table(period_table)
    
    # Кнопки для дополнительных действий
    put_markdown("## Дополнительные отчеты и анализ")
    put_buttons(['Графическая статистика', 'Экспорт в CSV', 'PDF-отчет'], 
               [show_graphic_statistics, 
                export_statistics_to_csv, 
                generate_statistics_report_pdf])
    
    put_button("В главное меню", onclick=lambda: main_menu(_thread_locals.username))

def show_graphic_statistics():
    """
    Отображение графической статистики по полисам ОСАГО
    """
    try:
        import matplotlib.pyplot as plt
        import io
        import base64
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        
        clear()
        put_markdown("# Графическая статистика")
        
        with app.app_context():
            current_date = datetime.now()
            
            # Данные для круговой диаграммы статусов полисов
            active_policies = Policy.query.filter_by(status='active').filter(Policy.end_date >= current_date).count()
            cancelled_policies = Policy.query.filter_by(status='cancelled').count()
            expired_policies = Policy.query.filter(Policy.status == 'active', Policy.end_date < current_date).count()
            
            # Данные для диаграммы по периодам полисов
            period_data = {}
            all_policies = Policy.query.all()
            for policy in all_policies:
                days = (policy.end_date - policy.start_date).days
                if days <= 100:  # ~3 месяца
                    period = "3 месяца"
                elif days <= 190:  # ~6 месяцев
                    period = "6 месяцев"
                else:
                    period = "12 месяцев"
                
                period_data[period] = period_data.get(period, 0) + 1
                
            # Данные по месяцам
            monthly_data = {}
            for policy in all_policies:
                month = policy.created_at.strftime('%Y-%m')
                monthly_data[month] = monthly_data.get(month, 0) + 1
            
            # Отсортированные данные по месяцам для графика
            sorted_months = sorted(monthly_data.keys())
            monthly_counts = [monthly_data[month] for month in sorted_months]
        
        # Создаем фигуру с тремя диаграммами
        fig = Figure(figsize=(15, 10))
        fig.subplots_adjust(hspace=0.4)  # Добавляем вертикальное пространство между графиками
        
        # 1. Круговая диаграмма статусов полисов
        ax1 = fig.add_subplot(2, 2, 1)
        status_labels = ['Активные', 'Отмененные', 'Истекшие']
        status_values = [active_policies, cancelled_policies, expired_policies]
        status_colors = ['#4CAF50', '#F44336', '#FFC107']
        
        # Исключаем нулевые значения для лучшего отображения
        non_zero_labels = []
        non_zero_values = []
        non_zero_colors = []
        for i, val in enumerate(status_values):
            if val > 0:
                non_zero_labels.append(status_labels[i])
                non_zero_values.append(val)
                non_zero_colors.append(status_colors[i])
                
        if sum(non_zero_values) > 0:
            ax1.pie(non_zero_values, labels=non_zero_labels, colors=non_zero_colors, autopct='%1.1f%%', startangle=90)
            ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
            ax1.set_title('Распределение полисов по статусам')
        else:
            ax1.text(0.5, 0.5, 'Нет данных для отображения', horizontalalignment='center', verticalalignment='center')
            
        # 2. Столбчатая диаграмма периодов полисов
        ax2 = fig.add_subplot(2, 2, 2)
        periods = list(period_data.keys())
        counts = list(period_data.values())
        
        if periods and counts:
            bars = ax2.bar(periods, counts, color='#2196F3')
            ax2.set_title('Распределение полисов по периодам')
            ax2.set_ylabel('Количество полисов')
            ax2.set_xlabel('Период')
            
            # Добавляем подписи с количеством над столбцами
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                         f'{int(height)}',
                         ha='center', va='bottom')
        else:
            ax2.text(0.5, 0.5, 'Нет данных для отображения', horizontalalignment='center', verticalalignment='center')
            
        # 3. График динамики оформления полисов по месяцам
        ax3 = fig.add_subplot(2, 1, 2)
        
        if sorted_months and monthly_counts:
            # Упрощаем названия месяцев для отображения
            display_months = [month.split('-')[1] + '/' + month.split('-')[0][2:] for month in sorted_months]
            
            ax3.plot(display_months, monthly_counts, marker='o', linestyle='-', color='#673AB7')
            ax3.set_title('Динамика оформления полисов по месяцам')
            ax3.set_ylabel('Количество полисов')
            ax3.set_xlabel('Месяц/Год')
            ax3.grid(True, linestyle='--', alpha=0.7)
            
            # Поворачиваем подписи по оси X для лучшей читаемости
            ax3.tick_params(axis='x', rotation=45)
            
            # Добавляем точные значения над точками графика
            for i, count in enumerate(monthly_counts):
                ax3.annotate(str(count), (display_months[i], monthly_counts[i]), 
                            textcoords="offset points", 
                            xytext=(0,10), 
                            ha='center')
        else:
            ax3.text(0.5, 0.5, 'Нет данных для отображения', horizontalalignment='center', verticalalignment='center')
            
        # Сохраняем изображение в память и конвертируем в base64
        canvas = FigureCanvasAgg(fig)
        buf = io.BytesIO()
        canvas.print_png(buf)
        data = base64.b64encode(buf.getbuffer()).decode("ascii")
        
        # Отображаем изображение
        put_markdown("## Визуализация статистики по полисам")
        put_html(f"<img src='data:image/png;base64,{data}' style='width:100%;'>")
        
    except ImportError:
        put_error("Для отображения графиков требуется установить библиотеку matplotlib")
        put_markdown("Выполните команду: `pip install matplotlib`")
        
    except Exception as e:
        put_error(f"Ошибка при создании графиков: {str(e)}")
    
    put_buttons(['Экспорт в CSV', 'PDF-отчет'], 
               [export_statistics_to_csv, 
                generate_statistics_report_pdf])
    put_button("Назад", onclick=lambda: show_statistics())

def export_statistics_to_csv():
    """
    Экспорт статистики по полисам в CSV-файл
    """
    try:
        import csv
        import tempfile
        import os
        import pandas as pd
        from datetime import date
        
        clear()
        put_markdown("# Экспорт статистики в CSV")
        
        with app.app_context():
            current_date = datetime.now()
            
            # Получаем данные о полисах
            policies = Policy.query.all()
            
            # Создаем DataFrame для полисов
            policy_data = []
            for policy in policies:
                vehicle = db.session.get(Vehicle, policy.vehicle_id)
                client = db.session.get(Client, vehicle.client_id) if vehicle else None
                
                # Определяем текущий статус
                if policy.status == 'cancelled':
                    status = 'Отменен'
                elif policy.end_date < current_date:
                    status = 'Истек'
                else:
                    status = 'Активен'
                    
                policy_data.append({
                    'Номер полиса': policy.number,
                    'Статус': status,
                    'Дата создания': policy.created_at.strftime('%d.%m.%Y'),
                    'Дата начала': policy.start_date.strftime('%d.%m.%Y'),
                    'Дата окончания': policy.end_date.strftime('%d.%m.%Y'),
                    'Стоимость': policy.cost,
                    'Марка ТС': vehicle.brand if vehicle else '',
                    'Модель ТС': vehicle.model if vehicle else '',
                    'Гос. номер': vehicle.reg_number if vehicle else '',
                    'Владелец': client.full_name if client else ''
                })
        
        if not policy_data:
            put_error("Нет данных для экспорта")
            put_button("Назад", onclick=lambda: show_statistics())
            return
            
        # Создаем DataFrame и сохраняем в CSV
        df = pd.DataFrame(policy_data)
          # Создаем файл в папке для загрузок
        current_date_str = date.today().strftime('%Y-%m-%d')
        file_name = f"policies_export_{current_date_str}.csv"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        
        # Сохраняем DataFrame в CSV
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
          # Создаем ссылку для скачивания прямо из статической директории
        filename = f"policies_export_{current_date_str}.csv"
        download_url = f"/download/files/{filename}"
        put_success("Данные успешно экспортированы в CSV")
        put_markdown(f"[Скачать CSV-файл]({download_url})")
        
    except ImportError:
        put_error("Для экспорта в CSV требуется установить библиотеку pandas")
        put_markdown("Выполните команду: `pip install pandas`")
        
    except Exception as e:
        put_error(f"Ошибка при экспорте данных: {str(e)}")
    
    put_button("Назад", onclick=lambda: show_statistics())

def generate_statistics_report_pdf():
    """
    Генерация PDF-отчета со статистикой по полисам
    """
    try:
        from fpdf import FPDF
        import tempfile
        import os
        from datetime import date
        
        clear()
        put_markdown("# Генерация PDF-отчета")
        
        with app.app_context():
            current_date = datetime.now()
            
            # Общие данные о полисах
            total_policies = Policy.query.count()
            active_policies = Policy.query.filter_by(status='active').filter(Policy.end_date >= current_date).count()
            cancelled_policies = Policy.query.filter_by(status='cancelled').count()
            expired_policies = Policy.query.filter(Policy.status == 'active', Policy.end_date < current_date).count()
            
            # Общая сумма по полисам
            total_sum = db.session.query(db.func.sum(Policy.cost)).scalar() or 0
            active_sum = db.session.query(db.func.sum(Policy.cost)).filter_by(status='active').filter(Policy.end_date >= current_date).scalar() or 0
            
            # Количество полисов по периодам (3, 6, 12 месяцев)
            period_data = {}
            all_policies = Policy.query.all()
            for policy in all_policies:
                days = (policy.end_date - policy.start_date).days
                if days <= 100:  # ~3 месяца
                    period = "3 месяца"
                elif days <= 190:  # ~6 месяцев
                    period = "6 месяцев"
                else:
                    period = "12 месяцев"
                
                period_data[period] = period_data.get(period, 0) + 1
            
            # Данные по месяцам
            monthly_data = {}
            for policy in all_policies:
                month = policy.created_at.strftime('%Y-%m')
                monthly_data[month] = monthly_data.get(month, 0) + 1
            
            # Последние 10 полисов
            recent_policies = (Policy.query
                              .join(Policy.vehicle)
                              .join(Vehicle.client)
                              .add_entity(Vehicle)
                              .add_entity(Client)
                              .order_by(Policy.created_at.desc())
                              .limit(10)
                              .all())
          # Создаем PDF документ с поддержкой кириллицы
        pdf = FPDF()
        # Добавляем кириллический шрифт (обычный и полужирный)
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'arial.ttf')
        pdf.add_font('CustomFont', '', font_path)
        pdf.add_font('CustomFont', 'B', font_path)
        pdf.add_page()
        
        # Добавляем шапку
        pdf.set_font("CustomFont", "B", 16)
        pdf.cell(0, 10, "СТАТИСТИЧЕСКИЙ ОТЧЕТ ПО ПОЛИСАМ ОСАГО", 0, 1, 'C')
        pdf.cell(0, 10, f"Дата формирования: {current_date.strftime('%d.%m.%Y')}", 0, 1, 'C')
        pdf.ln(10)
          # Общая статистика
        pdf.set_font("CustomFont", "B", 14)
        pdf.cell(0, 10, "1. Общая статистика по полисам", 0, 1)
        pdf.set_font("CustomFont", "", 12)
        pdf.cell(0, 8, f"Всего полисов: {total_policies}", 0, 1)
        pdf.cell(0, 8, f"Действующие полисы: {active_policies}", 0, 1)
        pdf.cell(0, 8, f"Отмененные полисы: {cancelled_policies}", 0, 1)
        pdf.cell(0, 8, f"Истекшие полисы: {expired_policies}", 0, 1)
        pdf.cell(0, 8, f"Общая сумма всех полисов: {round(total_sum, 2)} руб.", 0, 1)
        pdf.cell(0, 8, f"Общая сумма действующих полисов: {round(active_sum, 2)} руб.", 0, 1)
        pdf.ln(5)
        
        # Распределение по периодам
        pdf.set_font("CustomFont", "B", 14)
        pdf.cell(0, 10, "2. Распределение полисов по срокам", 0, 1)
        pdf.set_font("CustomFont", "", 12)
        for period, count in period_data.items():
            percent = round(count / total_policies * 100, 2) if total_policies > 0 else 0
            pdf.cell(0, 8, f"{period}: {count} полисов ({percent}%)", 0, 1)
        pdf.ln(5)
        
        # Последние оформленные полисы
        pdf.set_font("CustomFont", "B", 14)
        pdf.cell(0, 10, "3. Последние оформленные полисы", 0, 1)
        pdf.set_font("CustomFont", "", 10)
        
        if recent_policies:
            # Заголовки таблицы
            pdf.cell(40, 8, "Номер полиса", 1, 0, 'C')
            pdf.cell(50, 8, "Владелец", 1, 0, 'C')
            pdf.cell(40, 8, "ТС", 1, 0, 'C')
            pdf.cell(30, 8, "Стоимость", 1, 0, 'C')
            pdf.cell(30, 8, "Дата", 1, 1, 'C')
            
            # Данные таблицы
            for policy, vehicle, client in recent_policies:
                pdf.cell(40, 8, policy.number, 1, 0)
                pdf.cell(50, 8, client.full_name[:25], 1, 0)  # Ограничиваем длину имени
                pdf.cell(40, 8, f"{vehicle.brand} {vehicle.model}"[:20], 1, 0)
                pdf.cell(30, 8, f"{policy.cost} руб.", 1, 0)
                pdf.cell(30, 8, policy.created_at.strftime('%d.%m.%Y'), 1, 1)
        else:
            pdf.cell(0, 8, "Нет данных о полисах", 0, 1)
          # Создаем файл в папке для загрузок
        current_date_str = date.today().strftime('%Y-%m-%d')
        file_name = f"policies_report_{current_date_str}.pdf"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        
        try:
            # Сохраняем PDF в файл
            pdf.output(file_path)
            put_success("PDF-отчет успешно создан")
              # Создаем ссылку для скачивания прямо из статической директории
            filename = f"policies_report_{current_date_str}.pdf"
            download_url = f"/download/files/{filename}"
            put_markdown(f"[Скачать отчет {current_date_str}.pdf]({download_url})")
            
        except Exception as e:
            put_error(f"Ошибка при создании PDF: {str(e)}")
        
    except ImportError:
        put_error("Для создания PDF требуется установить библиотеку fpdf2.")
        put_markdown("Выполните команду: `pip install fpdf2`")
    
    put_button("Назад", onclick=lambda: show_statistics())

# Настройка статических маршрутов для файлов
@app.route('/download/files/<path:filename>', methods=['GET'])
def download_file(filename):
    """Маршрут для скачивания файлов из статической директории"""
    try:
        download_name = filename  # Имя файла при скачивании
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Проверка существует ли файл
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_file(file_path, as_attachment=True, download_name=download_name)
        else:
            return "Файл не найден", 404
    except Exception as e:
        return f"Ошибка при скачивании файла: {str(e)}", 500

@app.route('/', methods=['GET', 'POST'])
def index():
    return webio_view(login)()

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask
from models import db, Client, Vehicle, Policy
from sqlalchemy import text
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///osago.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Тестовые данные клиентов
test_clients = [
    {
        "full_name": "Иванов Иван Иванович",
        "passport": "4512 356789",
        "phone": "+79001234567",
        "email": "ivanov@mail.ru"
    },
    {
        "full_name": "Петров Петр Петрович",
        "passport": "4513 567890",
        "phone": "+79002345678",
        "email": "petrov@gmail.com"
    },
    {
        "full_name": "Сидорова Анна Ивановна",
        "passport": "4514 678901",
        "phone": "+79003456789",
        "email": "sidorova@yandex.ru"
    },
    {
        "full_name": "Кузнецов Алексей Сергеевич",
        "passport": "4515 789012",
        "phone": "+79004567890",
        "email": "kuznetsov@mail.ru"
    },
    {
        "full_name": "Смирнова Елена Павловна",
        "passport": "4516 890123",
        "phone": "+79005678901",
        "email": "smirnova@gmail.com"
    },
    {
        "full_name": "Соколов Дмитрий Александрович",
        "passport": "4517 901234",
        "phone": "+79006789012",
        "email": "sokolov@yandex.ru"
    },
    {
        "full_name": "Попова Мария Викторовна",
        "passport": "4518 012345",
        "phone": "+79007890123",
        "email": "popova@mail.ru"
    },
    {
        "full_name": "Лебедев Игорь Николаевич",
        "passport": "4519 123456",
        "phone": "+79008901234",
        "email": "lebedev@gmail.com"
    },
    {
        "full_name": "Новикова Ольга Андреевна",
        "passport": "4520 234567",
        "phone": "+79009012345",
        "email": "novikova@yandex.ru"
    },
    {
        "full_name": "Морозов Артём Дмитриевич",
        "passport": "4521 345678",
        "phone": "+79010123456",
        "email": "morozov@mail.ru"
    },
    {
        "full_name": "Волкова Светлана Игоревна",
        "passport": "4522 456789",
        "phone": "+79011234567",
        "email": "volkova@gmail.com"
    },
    {
        "full_name": "Зайцев Михаил Владимирович",
        "passport": "4523 567890",
        "phone": "+79012345678",
        "email": "zaitsev@yandex.ru"
    },
    {
        "full_name": "Семенова Наталья Алексеевна",
        "passport": "4524 678901",
        "phone": "+79013456789",
        "email": "semenova@mail.ru"
    },
    {
        "full_name": "Голубев Владислав Сергеевич",
        "passport": "4525 789012",
        "phone": "+79014567890",
        "email": "golubev@gmail.com"
    },
    {
        "full_name": "Виноградова Екатерина Михайловна",
        "passport": "4526 890123",
        "phone": "+79015678901",
        "email": "vinogradova@yandex.ru"
    }
]

# Тестовые данные транспортных средств
car_brands = [
    "Toyota", "Volkswagen", "Hyundai", "Kia", "Renault", 
    "Mercedes-Benz", "BMW", "Audi", "Skoda", "Ford", 
    "Nissan", "Honda", "Chevrolet", "Mazda", "Lexus"
]

car_models = {
    "Toyota": ["Camry", "Corolla", "RAV4", "Land Cruiser", "Highlander"],
    "Volkswagen": ["Polo", "Golf", "Passat", "Tiguan", "Touareg"],
    "Hyundai": ["Solaris", "Elantra", "Tucson", "Santa Fe", "Creta"],
    "Kia": ["Rio", "Optima", "Sportage", "Sorento", "Cerato"],
    "Renault": ["Logan", "Sandero", "Duster", "Kaptur", "Arkana"],
    "Mercedes-Benz": ["A-Class", "C-Class", "E-Class", "S-Class", "GLC"],
    "BMW": ["1 Series", "3 Series", "5 Series", "7 Series", "X5"],
    "Audi": ["A3", "A4", "A6", "Q3", "Q5"],
    "Skoda": ["Octavia", "Rapid", "Superb", "Kodiaq", "Karoq"],
    "Ford": ["Focus", "Mondeo", "Kuga", "Explorer", "Mustang"],
    "Nissan": ["Almera", "Qashqai", "X-Trail", "Juke", "Murano"],
    "Honda": ["Civic", "Accord", "CR-V", "Pilot", "HR-V"],
    "Chevrolet": ["Cruze", "Malibu", "Captiva", "Tahoe", "Camaro"],
    "Mazda": ["3", "6", "CX-5", "CX-9", "MX-5"],
    "Lexus": ["IS", "ES", "GS", "RX", "LX"]
}

def generate_random_vin():
    chars = "0123456789ABCDEFGHJKLMNPRSTUVWXYZ"  # VIN не содержит I, O и Q
    return ''.join(random.choice(chars) for _ in range(17))

def generate_reg_number():
    letters = "АВЕКМНОРСТУХ"  # Буквы, используемые в российских номерах
    region_codes = ["77", "78", "50", "99", "97", "777", "197", "750"]
    
    letter1 = random.choice(letters)
    digits = str(random.randint(0, 999)).zfill(3)
    letter2 = random.choice(letters)
    letter3 = random.choice(letters)
    region = random.choice(region_codes)
    
    return f"{letter1}{digits}{letter2}{letter3} {region}"

def generate_test_data():
    with app.app_context():
        # Проверим, есть ли уже данные в базе
        client_count = db.session.query(db.func.count(Client.id)).scalar()
        if client_count > 0:
            print(f"В базе данных уже есть {client_count} клиентов. Хотите добавить еще? (y/n)")
            response = input().lower()
            if response != 'y':
                print("Создание тестовых данных отменено.")
                return
        
        # Добавление клиентов
        created_clients = []
        for client_data in test_clients:
            try:
                # Проверяем, существует ли клиент с таким паспортом
                existing_client = Client.query.filter_by(passport=client_data["passport"]).first()
                if existing_client:
                    print(f"Клиент с паспортом {client_data['passport']} уже существует")
                    created_clients.append(existing_client)
                    continue
                    
                client = Client(**client_data)
                db.session.add(client)
                db.session.commit()
                print(f"Добавлен клиент: {client_data['full_name']}")
                created_clients.append(client)
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при добавлении клиента {client_data['full_name']}: {str(e)}")
        
        # Добавление транспортных средств для каждого клиента
        for client in created_clients:
            brand = random.choice(car_brands)
            model = random.choice(car_models[brand])
            current_year = datetime.now().year
            year = random.randint(current_year - 15, current_year)
            
            # Генерируем уникальный VIN
            while True:
                vin = generate_random_vin()
                existing_vehicle = Vehicle.query.filter_by(vin=vin).first()
                if not existing_vehicle:
                    break
            
            # Генерируем уникальный регистрационный номер
            while True:
                reg_number = generate_reg_number()
                existing_vehicle = Vehicle.query.filter_by(reg_number=reg_number).first()
                if not existing_vehicle:
                    break
              # Мощность двигателя
            engine_power = random.randint(75, 350)
            
            try:
                vehicle = Vehicle(
                    client_id=client.id,
                    brand=brand,
                    model=model,
                    year=year,
                    vin=vin,
                    reg_number=reg_number,
                    engine_power=engine_power
                )
                db.session.add(vehicle)
                db.session.commit()
                print(f"Добавлено ТС: {brand} {model}, {year}, {reg_number} для клиента {client.full_name}")
                  
                # История полисов для этого ТС (1-3 полиса, но только один активный)
                policy_count = random.randint(1, 3)
                
                # Создаем историю полисов
                for i in range(policy_count):
                    # Определяем период полиса
                    period_months = random.choice([3, 6, 12])
                    
                    # Определяем даты в зависимости от номера полиса в истории
                    if i == 0 and policy_count > 1:  # Самый старый полис (если есть несколько)
                        # Полис, который был давно (больше года назад)
                        start_date = datetime.now() - timedelta(days=random.randint(400, 700))
                        end_date = start_date + timedelta(days=30*period_months)
                        # Всегда истекший или отмененный
                        status = 'cancelled' if random.random() > 0.5 else 'active'  # активный но с истекшим сроком
                    elif i == policy_count - 1:  # Самый новый полис
                        # Текущий полис (в пределах 3 месяцев)
                        start_date = datetime.now() - timedelta(days=random.randint(0, 30))
                        end_date = start_date + timedelta(days=30*period_months)
                        # С большей вероятностью активный
                        status = 'active' if random.random() > 0.3 else 'cancelled'
                    else:  # Средний полис в истории
                        # Между старым и новым полисом
                        start_date = datetime.now() - timedelta(days=random.randint(150, 350))
                        end_date = start_date + timedelta(days=30*period_months)
                        # Истекший или отмененный
                        status = 'cancelled' if random.random() > 0.5 else 'active'  # активный но с истекшим сроком
                    
                    # Проверяем действительность полиса (полис не может быть активен, если срок истек)
                    if status == 'active' and end_date < datetime.now():
                        # Это "бывший активный", но истекший полис
                        pass  # оставляем статус 'active', но при отображении он будет показываться как истекший
                    
                    # Стоимость полиса
                    base_cost = 5000
                    # Коэффициенты для расчета стоимости
                    power_factor = 1.0 + (vehicle.engine_power - 100) / 200  # От 0.6 до 2.0 в зависимости от мощности
                    age_factor = 1.0 + (current_year - vehicle.year) / 20  # Старше - дороже
                    
                    cost = base_cost * power_factor * age_factor * (period_months / 12)
                    cost = round(cost, 2)
                    
                    # Генерируем номер полиса
                    prefix = "OSG"
                    date_part = start_date.strftime('%Y%m%d')
                    random_part = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                    policy_number = f"{prefix}-{date_part}-{random_part}"
                    
                    # Примечания для отмененных полисов
                    notes = None
                    if status == 'cancelled':
                        cancel_reasons = [
                            "По желанию клиента",
                            "Прекращение права собственности на ТС",
                            "Утилизация ТС",
                            "Продажа ТС",
                            "Полная гибель ТС в ДТП"
                        ]
                        notes = random.choice(cancel_reasons)
                    
                    policy = Policy(
                        number=policy_number,
                        vehicle_id=vehicle.id,
                        start_date=start_date,
                        end_date=end_date,
                        cost=cost,
                        created_at=start_date,
                        status=status,
                        notes=notes
                    )
                    db.session.add(policy)
                    db.session.commit()
                    
                    policy_status = "активный"
                    if status == 'cancelled':
                        policy_status = "отмененный"
                    elif end_date < datetime.now():
                        policy_status = "истекший"
                    
                    print(f"Добавлен {policy_status} полис: {policy_number}, период: {period_months} мес., стоимость: {cost} руб.")
                
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка при добавлении ТС для клиента {client.full_name}: {str(e)}")
        
        print("\nСоздание тестовых данных завершено!")
        
        # Вывод статистики
        client_count = db.session.query(db.func.count(Client.id)).scalar()
        vehicle_count = db.session.query(db.func.count(Vehicle.id)).scalar()
        policy_count = db.session.query(db.func.count(Policy.id)).scalar()
        active_policies = db.session.query(db.func.count(Policy.id)).filter_by(status='active').scalar()
        cancelled_policies = db.session.query(db.func.count(Policy.id)).filter_by(status='cancelled').scalar()
        
        print(f"\nВсего в базе данных:")
        print(f"Клиентов: {client_count}")
        print(f"Транспортных средств: {vehicle_count}")
        print(f"Полисов: {policy_count}")
        print(f"  - Активных полисов: {active_policies}")
        print(f"  - Отмененных полисов: {cancelled_policies}")

if __name__ == "__main__":
    generate_test_data()

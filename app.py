import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import random

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    
    # Таблица заявок (ваша структура)
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issuer_name TEXT,
            new_issuer TEXT,
            ep_bum TEXT,
            date_declaration TEXT,
            accelerated_rate TEXT,
            service_type TEXT,
            prospect_exists TEXT,
            expert_deadline_max TEXT,
            decision_deadline_max TEXT,
            suspension TEXT,
            suspension_date TEXT,
            resumption_date TEXT,
            expert_report_date TEXT,
            service_done_date TEXT,
            cb_registration TEXT,
            executor TEXT,
            curator TEXT,
            num_issues TEXT,
            organizer TEXT,
            contact_person TEXT,
            notes TEXT,
            features TEXT,
            n_flag TEXT,
            u_flag TEXT,
            updated_by TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица сотрудников
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            position TEXT,
            skills TEXT,
            workload INTEGER,
            available BOOLEAN,
            notes TEXT
        )
    ''')
    
    # Полный список всех типов услуг
    all_service_types = [
        "1 уровень",
        "2 уровень",
        "3 уровень",
        "доп.выпуск",
        "Программа",
        "Проспект",
        "Предв. рассм.",
        "Изменения",
        "Изменения (ОСВО)",
        "Изменения (реорганизация)",
        "Уведомление ПВО",
        "Уведомление о сост. проспекта (отдельно)",
        "Доп. выпуск",
        "Признание несост."
    ]
    all_skills = ", ".join(all_service_types)
    
    # Добавим тестовых сотрудников, если пусто
    c.execute("SELECT COUNT(*) FROM employees")
    if c.fetchone()[0] == 0:
        employees = [
            ("Иван Петров", "Исполнитель", all_skills, 2, True, ""),
            ("Мария Сидорова", "Исполнитель", all_skills, 1, True, ""),
            ("Алексей Козлов", "Куратор", all_skills, 3, True, ""),
            ("Ольга Волкова", "Исполнитель", all_skills, 4, False, "Отпуск"),
            ("Дмитрий Морозов", "Куратор", all_skills, 1, True, ""),
        ]
        c.executemany('''
            INSERT INTO employees (name, position, skills, workload, available, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', employees)
    
    conn.commit()
    conn.close()

# Загрузка заявок
def load_applications():
    conn = sqlite3.connect('data.db')
    df = pd.read_sql_query("SELECT * FROM applications ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# Загрузка сотрудников
def load_employees():
    conn = sqlite3.connect('data.db')
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    return df

# Сохранение заявки
def save_application(data, user):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO applications (
            issuer_name, new_issuer, ep_bum, date_declaration, accelerated_rate, service_type,
            prospect_exists, expert_deadline_max, decision_deadline_max, suspension,
            suspension_date, resumption_date, expert_report_date, service_done_date,
            cb_registration, executor, curator, num_issues, organizer, contact_person,
            notes, features, n_flag, u_flag, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    conn.close()

# Рекомендация исполнителя
def recommend_executor(service_type, organizer, accelerated_rate):
    employees = load_employees()
    executors = employees[
        (employees['position'] == 'Исполнитель') &
        (employees['available'] == True)
    ]
    
    if len(executors) == 0:
        return None, "Нет доступных исполнителей."
    
    service_type = service_type.strip()
    executors['match'] = executors['skills'].str.contains(service_type, na=False, case=False)
    executors = executors[executors['match'] == True]
    
    if len(executors) == 0:
        # Если нет совпадений — выбираем самого свободного (все умеют всё)
        executors = executors.sort_values(['workload'], ascending=[True])
        best = executors.iloc[0]
        reason = f"Выбран {best['name']} — самый свободный исполнитель (все умеют всё)."
        return best['name'], reason
    
    executors = executors.sort_values(['workload'], ascending=[True])
    best = executors.iloc[0]
    reason = f"Выбран {best['name']} потому что: ✅ доступен, ✅ имеет навык '{service_type}', " \
             f"❗ текущая загрузка: {best['workload']} заявок (самая низкая)."
    
    return best['name'], reason

# Рекомендация куратора
def recommend_curator(organizer, service_type):
    employees = load_employees()
    curators = employees[
        (employees['position'] == 'Куратор') &
        (employees['available'] == True)
    ]
    
    if len(curators) == 0:
        return None, "Нет доступных кураторов."
    
    service_type = service_type.strip()
    organizer = organizer.strip()
    
    curators['match_service'] = curators['skills'].str.contains(service_type, na=False, case=False)
    curators['match_organizer'] = curators['skills'].str.contains(organizer, na=False, case=False)
    curators['match'] = curators['match_service'] | curators['match_organizer']
    curators = curators[curators['match'] == True]
    
    if len(curators) == 0:
        curators = curators.sort_values(['workload'], ascending=[True])
        best = curators.iloc[0]
        reason = f"Выбран {best['name']} — самый свободный куратор (нет точного совпадения по навыкам)."
        return best['name'], reason
    
    curators = curators.sort_values(['workload'], ascending=[True])
    best = curators.iloc[0]
    reason = f"Выбран {best['name']} потому что: ✅ доступен, ✅ имеет опыт с '{service_type}' или '{organizer}', " \
             f"❗ загрузка: {best['workload']} заявок."
    
    return best['name'], reason

# Получить список исполнителей (только исполнители)
def get_executors():
    employees = load_employees()
    return employees[employees['position'] == 'Исполнитель']['name'].tolist()

# Получить список кураторов (только кураторы)
def get_curators():
    employees = load_employees()
    return employees[employees['position'] == 'Куратор']['name'].tolist()

# Случайный другой исполнитель (не текущий)
def get_random_other_executor(current_executor):
    executors = get_executors()
    if current_executor in executors:
        executors.remove(current_executor)
    if executors:
        return random.choice(executors)
    return None

# Случайный другой куратор (не текущий)
def get_random_other_curator(current_curator):
    curators = get_curators()
    if current_curator in curators:
        curators.remove(current_curator)
    if curators:
        return random.choice(curators)
    return None

# Инициализация
init_db()

st.set_page_config(page_title="Умная система регистрации эмитентов", layout="wide")
st.title("🧠 Умная система регистрации эмитентов в ЦБ РФ (вместо Excel)")

# --- Просмотр заявок ---
st.subheader("📋 Текущие заявки")
apps = load_applications()
if len(apps) > 0:
    display_columns = [
        'issuer_name', 'new_issuer', 'ep_bum', 'date_declaration', 'accelerated_rate',
        'service_type', 'prospect_exists', 'expert_deadline_max', 'decision_deadline_max',
        'suspension', 'suspension_date', 'resumption_date', 'expert_report_date',
        'service_done_date', 'cb_registration', 'executor', 'curator', 'num_issues',
        'organizer', 'contact_person', 'notes', 'features', 'n_flag', 'u_flag', 'timestamp'
    ]
    
    apps_display = apps[display_columns].copy()
    date_cols = [
        'date_declaration', 'expert_deadline_max', 'decision_deadline_max',
        'suspension_date', 'resumption_date', 'expert_report_date', 'service_done_date', 'timestamp'
    ]
    
    for col in date_cols:
        if col in apps_display.columns:
            apps_display[col] = pd.to_datetime(apps_display[col], errors='coerce').dt.strftime('%d.%m.%Y')
    
    column_labels = {
        'issuer_name': 'Наименование эмитента',
        'new_issuer': 'Новый эмитент',
        'ep_bum': 'ЭП/бум.',
        'date_declaration': 'Дата заявления',
        'accelerated_rate': 'Ускоренный тариф',
        'service_type': 'Раздел Списка',
        'prospect_exists': 'Наличие проспекта',
        'expert_deadline_max': 'Дата экспертного, макс.',
        'decision_deadline_max': 'Дата решения, макс.',
        'suspension': 'Приостановка',
        'suspension_date': 'Дата приостановки',
        'resumption_date': 'Дата возобновления',
        'expert_report_date': 'Дата экспертного заключения',
        'service_done_date': 'Дата оказания услуги',
        'cb_registration': 'Рег. действие в ЦБ',
        'executor': 'Исполнитель',
        'curator': 'Куратор',
        'num_issues': 'Кол-во выпусков/программ',
        'organizer': 'Организатор',
        'contact_person': 'Контактное лицо',
        'notes': 'Примечания',
        'features': 'Особенности',
        'n_flag': 'Н',
        'u_flag': 'Ю',
        'timestamp': 'Дата создания'
    }
    
    apps_display = apps_display.rename(columns=column_labels)
    st.dataframe(apps_display, use_container_width=True)
else:
    st.info("Нет заявок. Добавьте первую!")

# --- Просмотр сотрудников ---
st.subheader("👥 Сотрудники (для редактирования)")
employees = load_employees()
st.dataframe(employees, use_container_width=True)

# --- Форма для руководителя ---
st.subheader("✏️ Добавить новую заявку и получить рекомендации")

user = st.text_input("Ваше имя (для доступа к редактированию)", key="user")
if user != "Руководитель":
    st.info("🔒 Только руководитель может добавлять заявки и получать рекомендации. Введите 'Руководитель'")
else:
    with st.form("application_form"):
        st.subheader("📌 Основная информация")
        issuer_name = st.text_input("Наименование эмитента")
        new_issuer = st.selectbox("Новый эмитент", ["Да", "Нет"])
        ep_bum = st.text_input("ЭП/бум.")
        date_declaration = st.date_input("Дата заявления (дата принятия)")
        accelerated_rate = st.selectbox("Ускоренный тариф", ["Да", "Нет"])
        
        # Обязательный выпадающий список
        service_type_options = [
            "1 уровень",
            "2 уровень",
            "3 уровень",
            "доп.выпуск",
            "Программа",
            "Проспект",
            "Предв. рассм.",
            "Изменения",
            "Изменения (ОСВО)",
            "Изменения (реорганизация)",
            "Уведомление ПВО",
            "Уведомление о сост. проспекта (отдельно)",
            "Доп. выпуск",
            "Признание несост."
        ]
        service_type = st.selectbox("🔹 *Раздел Списка (тип услуги)* (обязательно)", service_type_options, help="Выберите один из предложенных типов услуги")
        
        prospect_exists = st.selectbox("Наличие проспекта", ["Да", "Нет", "Не определено"])
        expert_deadline_max = st.date_input("Дата экспертного, макс.")
        decision_deadline_max = st.date_input("Дата решения, макс.")
        suspension = st.selectbox("Приостановка", ["Да", "Нет"])
        suspension_date = st.date_input("Дата приостановки срока", value=None)
        resumption_date = st.date_input("Дата возобновления срока", value=None)
        expert_report_date = st.date_input("Дата экспертного заключения", value=None)
        service_done_date = st.date_input("Дата оказания услуги", value=None)
        cb_registration = st.text_input("Рег. действие в ЦБ")
        
        st.subheader("👥 Ответственные")
        
        # Получаем списки
        all_employees = load_employees()['name'].tolist()  # Все сотрудники — и исполнители, и кураторы
        curators_list = load_employees()[load_employees()['position'] == 'Куратор']['name'].tolist()
        
        # --- ОБНОВЛЕНИЕ ПОЛЕЙ ФОРМЫ В РЕАЛЬНОМ ВРЕМЕНИ ---
        # Если в сессии есть выбранная рекомендация — используем её как значение по умолчанию
        if 'selected_executor' in st.session_state and st.session_state.selected_executor:
            default_executor = st.session_state.selected_executor
        else:
            default_executor = ""  # или None, но лучше пустая строка для selectbox

        if 'selected_curator' in st.session_state and st.session_state.selected_curator:
            default_curator = st.session_state.selected_curator
        else:
            default_curator = ""

        # --- ПОЛЯ ФОРМЫ — СВЯЗАНЫ С session_state ---
        executor = st.selectbox(
            "Исполнитель", 
            [""] + all_employees, 
            index=(all_employees.index(default_executor) + 1) if default_executor in all_employees else 0,
            key="executor_select",
            help="Выберите любого сотрудника — исполнителя или куратора"
        )

        curator = st.selectbox(
            "Куратор", 
            [""] + curators_list, 
            index=(curators_list.index(default_curator) + 1) if default_curator in curators_list else 0,
            key="curator_select",
            help="Выберите только куратора из списка"
        )

        # --- Сохраняем выбранные значения в session_state при изменении ---
        # Это гарантирует, что при ручном выборе — система запоминает
        if executor != "":
            st.session_state.selected_executor = executor
        if curator != "":
            st.session_state.selected_curator = curator

        st.subheader("📌 Дополнительно")
        num_issues = st.text_input("Кол-во выпусков/программ")
        organizer = st.text_input("Организатор")
        contact_person = st.text_input("Контактное лицо")
        notes = st.text_area("Примечания")
        features = st.text_area("Особенности")
        n_flag = st.selectbox("Н", ["Да", "Нет"])
        u_flag = st.selectbox("Ю", ["Да", "Нет"])

        # --- КНОПКИ В ФОРМЕ — ВСЕ В ОДНОЙ СТРОКЕ, ИНТУИТИВНО ---
        st.markdown("---")
        st.subheader("⚡ Действия")

        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        with col1:
            get_recommendations = st.form_submit_button("🔍 Получить рекомендации", type="secondary", use_container_width=True)

        with col2:
            select_recommended = st.form_submit_button("✅ Выбрать рекомендованных", type="primary", use_container_width=True)

        with col3:
            suggest_other_executor = st.form_submit_button("🔄 Другой исполнитель", type="secondary", use_container_width=True)

        with col4:
            suggest_other_curator = st.form_submit_button("🔄 Другой куратор", type="secondary", use_container_width=True)

        # --- ЛОГИКА КНОПОК ---
        if get_recommendations:
            if not service_type:
                st.error("❗ **Раздел Списка (тип услуги)** — обязательное поле. Выберите значение из списка.")
            else:
                # Рекомендация исполнителя
                rec_exec, reason_exec = recommend_executor(service_type, organizer, accelerated_rate)
                if rec_exec:
                    st.success(f"✅ **Рекомендуем исполнителя: {rec_exec}**")
                    st.info(f"💡 **Почему?** {reason_exec}")
                    st.session_state.recommended_executor = rec_exec
                    st.session_state.reason_executor = reason_exec
                    st.session_state.selected_executor = rec_exec  # Автоматически выбираем
                else:
                    st.warning(f"⚠️ {reason_exec}")
                    st.session_state.recommended_executor = None
                    st.session_state.reason_executor = None
                    st.session_state.selected_executor = None
                
                # Рекомендация куратора
                rec_cur, reason_cur = recommend_curator(organizer, service_type)
                if rec_cur:
                    st.success(f"✅ **Рекомендуем куратора: {rec_cur}**")
                    st.info(f"💡 **Почему?** {reason_cur}")
                    st.session_state.recommended_curator = rec_cur
                    st.session_state.reason_curator = reason_cur
                    st.session_state.selected_curator = rec_cur  # Автоматически выбираем
                else:
                    st.warning(f"⚠️ {reason_cur}")
                    st.session_state.recommended_curator = None
                    st.session_state.reason_curator = None
                    st.session_state.selected_curator = None

        # --- ОТОБРАЖЕНИЕ РЕКОМЕНДАЦИЙ — ВСЕГДА, ДАЖЕ ПОСЛЕ СМЕНЫ СОТРУДНИКА ---
        if 'recommended_executor' in st.session_state and st.session_state.recommended_executor:
            st.markdown(f"**🔹 Рекомендация исполнителя:** `{st.session_state.recommended_executor}`")
            st.markdown(f"**💡 Причина:** {st.session_state.reason_executor}")

        if 'recommended_curator' in st.session_state and st.session_state.recommended_curator:
            st.markdown(f"**🔹 Рекомендация куратора:** `{st.session_state.recommended_curator}`")
            st.markdown(f"**💡 Причина:** {st.session_state.reason_curator}")

        # --- СМЕНА СОТРУДНИКА — ПЕРЕСЧИТЫВАЕМ РЕКОМЕНДАЦИЮ ДЛЯ НОВОГО СОТРУДНИКА ---
        if suggest_other_executor:
            if 'recommended_executor' in st.session_state and st.session_state.recommended_executor:
                # Получаем всех исполнителей, кроме текущего рекомендованного
                current_recommended = st.session_state.recommended_executor
                executors = [e for e in all_employees if e != current_recommended and e in load_employees()[load_employees()['position'] == 'Исполнитель']['name'].tolist()]
                
                if executors:
                    # Выбираем следующего лучшего по загруженности
                    next_exec, next_reason = recommend_executor(service_type, organizer, accelerated_rate)
                    # Но фильтруем, чтобы не вернуть текущего
                    if next_exec == current_recommended and len(executors) > 0:
                        # Принудительно выбираем следующего
                        next_exec = executors[0]
                        # Пересчитываем причину — упрощённо
                        next_reason = f"Выбран {next_exec} — следующий по загруженности после {current_recommended}."
                    
                    st.session_state.recommended_executor = next_exec
                    st.session_state.reason_executor = next_reason
                    st.session_state.selected_executor = next_exec
                    st.success(f"✅ Новая рекомендация: {next_exec}")
                    st.info(f"💡 Причина: {next_reason}")
                else:
                    st.warning("Нет других исполнителей.")
            else:
                st.warning("Сначала получите рекомендацию.")
            st.rerun()

        if suggest_other_curator:
            if 'recommended_curator' in st.session_state and st.session_state.recommended_curator:
                current_recommended = st.session_state.recommended_curator
                curators = [c for c in curators_list if c != current_recommended]
                
                if curators:
                    next_cur, next_reason = recommend_curator(organizer, service_type)
                    if next_cur == current_recommended and len(curators) > 0:
                        next_cur = curators[0]
                        next_reason = f"Выбран {next_cur} — следующий по загруженности после {current_recommended}."
                    
                    st.session_state.recommended_curator = next_cur
                    st.session_state.reason_curator = next_reason
                    st.session_state.selected_curator = next_cur
                    st.success(f"✅ Новая рекомендация: {next_cur}")
                    st.info(f"💡 Причина: {next_reason}")
                else:
                    st.warning("Нет других кураторов.")
            else:
                st.warning("Сначала получите рекомендацию.")
            st.rerun()

        # --- ВЫБОР РЕКОМЕНДОВАННЫХ — ОБНОВЛЯЕМ ПОЛЯ ФОРМЫ МГНОВЕННО ---
        if select_recommended:
            if 'recommended_executor' in st.session_state and st.session_state.recommended_executor:
                st.session_state.selected_executor = st.session_state.recommended_executor
            if 'recommended_curator' in st.session_state and st.session_state.recommended_curator:
                st.session_state.selected_curator = st.session_state.recommended_curator
            st.success("✅ Рекомендации применены!")
            st.rerun()

        # --- ПРИМЕНЕНИЕ ВЫБРАННЫХ — ОБНОВЛЕНИЕ ПОЛЕЙ ФОРМЫ В РЕАЛЬНОМ ВРЕМЕНИ ---
        if 'selected_executor' in st.session_state:
            executor = st.session_state.selected_executor
        if 'selected_curator' in st.session_state:
            curator = st.session_state.selected_curator

        # --- КНОПКА СОХРАНЕНИЯ ---
        if st.form_submit_button("💾 Сохранить заявку"):
            if not service_type:
                st.error("❗ **Раздел Списка (тип услуги)** — обязательное поле. Выберите значение из списка.")
            elif not issuer_name:
                st.error("❗ Заполните 'Наименование эмитента'")
            elif not executor:
                st.error("❗ Выберите исполнителя из списка")
            elif not curator:
                st.error("❗ Выберите куратора из списка")
            else:
                data = (
                    issuer_name, new_issuer, ep_bum, str(date_declaration), accelerated_rate, service_type,
                    prospect_exists, str(expert_deadline_max), str(decision_deadline_max), suspension,
                    str(suspension_date) if suspension_date else "", str(resumption_date) if resumption_date else "",
                    str(expert_report_date) if expert_report_date else "", str(service_done_date) if service_done_date else "",
                    cb_registration, executor, curator, num_issues, organizer, contact_person,
                    notes, features, n_flag, u_flag, user
                )
                save_application(data, user)
                st.success("✅ Заявка сохранена!")
                # Очищаем сессию
                for key in ['selected_executor', 'selected_curator', 'recommended_executor', 'recommended_curator', 'reason_executor', 'reason_curator']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
# --- Ручное назначение ---
st.subheader("🛠️ Ручное назначение исполнителя/куратора")
if user == "Руководитель":
    with st.form("manual_assign"):
        app_id = st.number_input("ID заявки (можно взять из таблицы выше)", min_value=1, step=1)
        new_executor = st.selectbox("Новый исполнитель", get_executors())
        new_curator = st.selectbox("Новый куратор", get_curators())
        
        if st.form_submit_button("🔄 Обновить ответственных"):
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute('''
                UPDATE applications SET executor = ?, curator = ?, updated_by = ? WHERE id = ?
            ''', (new_executor, new_curator, user, app_id))
            conn.commit()
            conn.close()
            st.success("✅ Ответственные обновлены!")
            st.rerun()
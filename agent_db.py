from __future__ import annotations

import sqlite3
from datetime import timedelta
from pathlib import Path

from config import CURRENT_MONTH_DAY, DB_PATH, LAST_MONTH_END, LAST_MONTH_START, TODAY, _iso

# Seed data merged from gardening_agent_seed.py
CARE_PROFILES = [
    {
        'common_name': 'Banana Plant',
        'category': 'fruiting tropical',
        'indoor_suitability': 0,
        'beginner_friendly': 0,
        'light_profile': 'full sun',
        'ideal_ph_min': 5.5,
        'ideal_ph_max': 7.0,
        'watering_note': 'Keep evenly moist and feed more often in warm weather.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Heavy feeder and fast grower.',
    },
    {
        'common_name': 'Cherry Tomatoes',
        'category': 'vegetable',
        'indoor_suitability': 0,
        'beginner_friendly': 1,
        'light_profile': 'full sun',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 6.8,
        'watering_note': 'Water deeply and keep foliage dry.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Best with steady moisture and airflow.',
    },
    {
        'common_name': 'Hibiscus',
        'category': 'flowering shrub',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'bright light',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 6.8,
        'watering_note': 'Likes regular water but not soggy soil.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Sensitive to heat spikes and dry wind.',
    },
    {
        'common_name': 'Succulents',
        'category': 'desert plants',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'bright light',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 7.5,
        'watering_note': 'Water only after the mix dries out fully.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Avoid watering in the hottest part of the day.',
    },
    {
        'common_name': 'Basil',
        'category': 'herb',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'bright indirect light',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 7.0,
        'watering_note': 'Keep soil evenly moist and pinch often.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Sensitive to heat and inconsistent watering.',
    },
    {
        'common_name': 'Mint',
        'category': 'herb',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'partial shade',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 7.0,
        'watering_note': 'Keep consistently damp, especially in containers.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Fast grower and easy to manage in a pot.',
    },
    {
        'common_name': 'Monstera',
        'category': 'houseplant',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'low to bright indirect light',
        'ideal_ph_min': 5.8,
        'ideal_ph_max': 6.5,
        'watering_note': 'Water when the top inch dries out.',
        'best_watering_time_hot_weather': 'morning',
        'notes': 'Repot when roots circle the pot.',
    },
    {
        'common_name': 'Snake Plant',
        'category': 'houseplant',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'low light tolerant',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 7.5,
        'watering_note': 'Allow the mix to dry almost fully between waterings.',
        'best_watering_time_hot_weather': 'morning',
        'notes': 'One of the easiest low-light plants.',
    },
    {
        'common_name': 'Rose',
        'category': 'flowering shrub',
        'indoor_suitability': 0,
        'beginner_friendly': 0,
        'light_profile': 'full sun',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 6.8,
        'watering_note': 'Deep watering once or twice a week is usually better than frequent shallow watering.',
        'best_watering_time_hot_weather': 'early morning',
        'notes': 'Prune after flowering and keep airflow open.',
    },
    {
        'common_name': 'ZZ Plant',
        'category': 'houseplant',
        'indoor_suitability': 1,
        'beginner_friendly': 1,
        'light_profile': 'low light tolerant',
        'ideal_ph_min': 6.0,
        'ideal_ph_max': 7.5,
        'watering_note': 'Water sparingly and avoid wet feet.',
        'best_watering_time_hot_weather': 'morning',
        'notes': 'Great beginner plant for low light.',
    },
]

PERSONAL_PLANTS = [
    {
        'name': 'Banana Plant',
        'species': 'Musa acuminata',
        'nickname': 'Tropicana',
        'location': 'Back Patio',
        'plant_type': 'outdoor',
        'status': 'active',
        'purchase_date': '2025-02-14',
        'watering_interval_days': 2,
        'last_watered': _iso(2),
        'last_fertilized': _iso(16),
        'last_repot': _iso(140),
        'sunlight_hours': 8.0,
        'optimal_ph_min': 5.5,
        'optimal_ph_max': 7.0,
        'notes': 'Heavy feeder and strong grower in warm weather.',
    },
    {
        'name': 'Tomato Plant',
        'species': 'Solanum lycopersicum',
        'nickname': 'Brandy',
        'location': 'Raised Bed',
        'plant_type': 'outdoor',
        'status': 'monitor',
        'purchase_date': '2025-03-10',
        'watering_interval_days': 2,
        'last_watered': _iso(1),
        'last_fertilized': _iso(12),
        'last_repot': _iso(0),
        'sunlight_hours': 8.5,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 6.8,
        'notes': 'Yellowing leaves and brown spotting need monitoring.',
    },
    {
        'name': 'Hibiscus',
        'species': 'Hibiscus rosa-sinensis',
        'nickname': 'Ruby',
        'location': 'Front Yard',
        'plant_type': 'outdoor',
        'status': 'active',
        'purchase_date': '2024-09-01',
        'watering_interval_days': 3,
        'last_watered': _iso(2),
        'last_fertilized': _iso(10),
        'last_repot': _iso(120),
        'sunlight_hours': 7.5,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 6.8,
        'notes': 'Heat sensitive in extreme afternoons.',
    },
    {
        'name': 'Monstera Deliciosa',
        'species': 'Monstera deliciosa',
        'nickname': 'Moss',
        'location': 'Living Room',
        'plant_type': 'indoor',
        'status': 'active',
        'purchase_date': '2024-05-11',
        'watering_interval_days': 7,
        'last_watered': _iso(6),
        'last_fertilized': _iso(20),
        'last_repot': _iso(64),
        'sunlight_hours': 5.5,
        'optimal_ph_min': 5.8,
        'optimal_ph_max': 6.5,
        'notes': 'Repotting history suggests it may be close to root bound.',
    },
    {
        'name': 'Sweet Basil',
        'species': 'Ocimum basilicum',
        'nickname': 'Pesto',
        'location': 'Kitchen Window',
        'plant_type': 'indoor',
        'status': 'sick',
        'purchase_date': '2025-04-12',
        'watering_interval_days': 2,
        'last_watered': _iso(3),
        'last_fertilized': _iso(18),
        'last_repot': _iso(45),
        'sunlight_hours': 6.5,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 7.0,
        'notes': 'Yellowing leaves and brown spots after recent heat.',
    },
    {
        'name': 'Mint',
        'species': 'Mentha spicata',
        'nickname': 'Sprig',
        'location': 'Herb Shelf',
        'plant_type': 'indoor',
        'status': 'active',
        'purchase_date': '2025-01-09',
        'watering_interval_days': 2,
        'last_watered': _iso(1),
        'last_fertilized': _iso(14),
        'last_repot': _iso(90),
        'sunlight_hours': 4.0,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 7.0,
        'notes': 'Fast growth, easy to compare against basil.',
    },
    {
        'name': 'Cucumber Vine',
        'species': 'Cucumis sativus',
        'nickname': 'Crunch',
        'location': 'Backyard Bed',
        'plant_type': 'outdoor',
        'status': 'monitor',
        'purchase_date': '2025-04-08',
        'watering_interval_days': 3,
        'last_watered': _iso(2),
        'last_fertilized': _iso(11),
        'last_repot': _iso(0),
        'sunlight_hours': 8.5,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 6.8,
        'notes': 'Humidity spikes caused mildew concern last season.',
    },
    {
        'name': 'Snake Plant',
        'species': 'Dracaena trifasciata',
        'nickname': 'Spear',
        'location': 'Office',
        'plant_type': 'indoor',
        'status': 'inactive',
        'purchase_date': '2024-11-16',
        'watering_interval_days': 21,
        'last_watered': _iso(18),
        'last_fertilized': _iso(60),
        'last_repot': _iso(250),
        'sunlight_hours': 2.0,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 7.5,
        'notes': 'Low-water plant, currently marked inactive.',
    },
    {
        'name': 'Succulent Mix',
        'species': 'Mixed succulents',
        'nickname': 'Desert Tray',
        'location': 'Sunny Shelf',
        'plant_type': 'indoor',
        'status': 'active',
        'purchase_date': '2024-08-19',
        'watering_interval_days': 14,
        'last_watered': _iso(10),
        'last_fertilized': _iso(40),
        'last_repot': _iso(180),
        'sunlight_hours': 6.0,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 7.5,
        'notes': 'Needs dry soil and morning watering during heat.',
    },
    {
        'name': 'Aloe Vera',
        'species': 'Aloe vera',
        'nickname': 'Gel',
        'location': 'Bedroom Shelf',
        'plant_type': 'indoor',
        'status': 'inactive',
        'purchase_date': '2024-07-20',
        'watering_interval_days': 21,
        'last_watered': _iso(22),
        'last_fertilized': _iso(70),
        'last_repot': _iso(300),
        'sunlight_hours': 5.0,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 7.0,
        'notes': 'Second inactive plant for demo queries.',
    },
    {
        'name': 'Rose',
        'species': 'Rosa spp.',
        'nickname': 'Velvet',
        'location': 'South Border',
        'plant_type': 'outdoor',
        'status': 'active',
        'purchase_date': '2024-03-14',
        'watering_interval_days': 4,
        'last_watered': _iso(2),
        'last_fertilized': _iso(15),
        'last_repot': _iso(150),
        'sunlight_hours': 7.0,
        'optimal_ph_min': 6.0,
        'optimal_ph_max': 6.8,
        'notes': 'Used for pruning tutorial and pest-control search.',
    },
]


def reset_database(db_path: Path = DB_PATH) -> None:
    if db_path.exists():
        db_path.unlink()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database(db_path: Path = DB_PATH) -> None:
    reset_database(db_path)
    conn = connect(db_path)
    try:
        conn.executescript(
            '''
            PRAGMA foreign_keys = ON;

            CREATE TABLE care_profiles (
                common_name TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                indoor_suitability INTEGER NOT NULL,
                beginner_friendly INTEGER NOT NULL,
                light_profile TEXT NOT NULL,
                temp_safe_low_c REAL NOT NULL,
                temp_safe_high_c REAL NOT NULL,
                ideal_ph_min REAL NOT NULL,
                ideal_ph_max REAL NOT NULL,
                watering_note TEXT NOT NULL,
                best_watering_time_hot_weather TEXT NOT NULL,
                notes TEXT
            );

            CREATE TABLE plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                species TEXT NOT NULL,
                nickname TEXT,
                location TEXT NOT NULL,
                plant_type TEXT NOT NULL,
                status TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                watering_interval_days INTEGER NOT NULL,
                last_watered TEXT NOT NULL,
                last_fertilized TEXT NOT NULL,
                last_repot TEXT NOT NULL,
                sunlight_hours REAL NOT NULL,
                optimal_ph_min REAL NOT NULL,
                optimal_ph_max REAL NOT NULL,
                notes TEXT
            );

            CREATE TABLE watering_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                frequency_days INTEGER NOT NULL,
                amount_ml INTEGER NOT NULL,
                season TEXT NOT NULL,
                next_due TEXT NOT NULL,
                moisture_threshold INTEGER NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE soil_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                reading_date TEXT NOT NULL,
                soil_ph REAL NOT NULL,
                moisture_percent INTEGER NOT NULL,
                temperature_c REAL NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE fertilizer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                application_date TEXT NOT NULL,
                fertilizer_name TEXT NOT NULL,
                npk_ratio TEXT NOT NULL,
                dosage_g REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE repotting_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                repot_date TEXT NOT NULL,
                pot_size_in REAL NOT NULL,
                root_bound INTEGER NOT NULL,
                notes TEXT,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE growth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                height_cm REAL NOT NULL,
                leaf_count INTEGER NOT NULL,
                bloom_count INTEGER NOT NULL DEFAULT 0,
                note TEXT,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                vendor TEXT,
                note TEXT,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE SET NULL
            );

            CREATE TABLE purchase_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                purchase_date TEXT NOT NULL,
                store TEXT NOT NULL,
                amount_usd REAL NOT NULL,
                items TEXT NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );

            CREATE TABLE shopping_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                priority TEXT NOT NULL DEFAULT 'medium',
                added_date TEXT NOT NULL,
                source TEXT
            );

            CREATE TABLE diagnostics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plant_id INTEGER NOT NULL,
                diagnosis_date TEXT NOT NULL,
                symptom TEXT NOT NULL,
                severity TEXT NOT NULL,
                likely_cause TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                FOREIGN KEY (plant_id) REFERENCES plants(id) ON DELETE CASCADE
            );
            '''
        )

        temp_ranges = {
            'Banana Plant': (20.0, 35.0),
            'Cherry Tomatoes': (15.0, 32.0),
            'Hibiscus': (18.0, 33.0),
            'Succulents': (16.0, 38.0),
            'Basil': (18.0, 32.0),
            'Mint': (15.0, 32.0),
            'Monstera': (18.0, 30.0),
            'Snake Plant': (15.0, 32.0),
            'Rose': (10.0, 33.0),
            'ZZ Plant': (18.0, 32.0),
        }
        care_profile_rows = []
        for profile in CARE_PROFILES:
            enriched = dict(profile)
            enriched['temp_safe_low_c'], enriched['temp_safe_high_c'] = temp_ranges[profile['common_name']]
            care_profile_rows.append(enriched)

        conn.executemany(
            '''
            INSERT INTO care_profiles (
                common_name, category, indoor_suitability, beginner_friendly,
                light_profile, temp_safe_low_c, temp_safe_high_c, ideal_ph_min, ideal_ph_max, watering_note,
                best_watering_time_hot_weather, notes
            ) VALUES (:common_name, :category, :indoor_suitability, :beginner_friendly,
                      :light_profile, :temp_safe_low_c, :temp_safe_high_c, :ideal_ph_min, :ideal_ph_max, :watering_note,
                      :best_watering_time_hot_weather, :notes)
            ''',
            care_profile_rows,
        )

        for plant in PERSONAL_PLANTS:
            cursor = conn.execute(
                '''
                INSERT INTO plants (
                    name, species, nickname, location, plant_type, status,
                    purchase_date, watering_interval_days, last_watered,
                    last_fertilized, last_repot, sunlight_hours,
                    optimal_ph_min, optimal_ph_max, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    plant['name'],
                    plant['species'],
                    plant['nickname'],
                    plant['location'],
                    plant['plant_type'],
                    plant['status'],
                    plant['purchase_date'],
                    plant['watering_interval_days'],
                    plant['last_watered'],
                    plant['last_fertilized'],
                    plant['last_repot'],
                    plant['sunlight_hours'],
                    plant['optimal_ph_min'],
                    plant['optimal_ph_max'],
                    plant['notes'],
                ),
            )
            plant_id = cursor.lastrowid

            water_amount = {
                'Banana Plant': 1200,
                'Tomato Plant': 650,
                'Hibiscus': 850,
                'Monstera Deliciosa': 500,
                'Sweet Basil': 300,
                'Mint': 260,
                'Cucumber Vine': 700,
                'Snake Plant': 180,
                'Succulent Mix': 140,
                'Aloe Vera': 120,
                'Rose': 600,
            }[plant['name']]

            moisture_threshold = {
                'Banana Plant': 45,
                'Tomato Plant': 40,
                'Hibiscus': 38,
                'Monstera Deliciosa': 35,
                'Sweet Basil': 42,
                'Mint': 46,
                'Cucumber Vine': 44,
                'Snake Plant': 20,
                'Succulent Mix': 18,
                'Aloe Vera': 18,
                'Rose': 36,
            }[plant['name']]

            conn.execute(
                '''
                INSERT INTO watering_schedules (
                    plant_id, frequency_days, amount_ml, season, next_due, moisture_threshold
                ) VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    plant_id,
                    plant['watering_interval_days'],
                    water_amount,
                    'spring',
                    (TODAY + timedelta(days=max(0, plant['watering_interval_days'] - 2))).isoformat(),
                    moisture_threshold,
                ),
            )

            ph_seed = {
                'Banana Plant': 6.2,
                'Tomato Plant': 6.4,
                'Hibiscus': 6.5,
                'Monstera Deliciosa': 6.1,
                'Sweet Basil': 6.0,
                'Mint': 6.5,
                'Cucumber Vine': 6.4,
                'Snake Plant': 6.8,
                'Succulent Mix': 7.1,
                'Aloe Vera': 6.9,
                'Rose': 6.4,
            }[plant['name']]
            moisture_seed = {
                'Banana Plant': 52,
                'Tomato Plant': 47,
                'Hibiscus': 44,
                'Monstera Deliciosa': 39,
                'Sweet Basil': 58,
                'Mint': 61,
                'Cucumber Vine': 55,
                'Snake Plant': 24,
                'Succulent Mix': 19,
                'Aloe Vera': 17,
                'Rose': 41,
            }[plant['name']]
            temp_seed = 22.5 if plant['plant_type'] == 'indoor' else 28.0

            for offset in range(5):
                conn.execute(
                    '''
                    INSERT INTO soil_readings (
                        plant_id, reading_date, soil_ph, moisture_percent, temperature_c
                    ) VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        plant_id,
                        _iso(4 - offset),
                        round(ph_seed + offset * 0.03, 2),
                        max(10, min(90, moisture_seed + (offset - 2) * 4)),
                        round(temp_seed + (0.4 * offset), 1),
                    ),
                )

            fertilize_dates = [15, 42] if plant['name'] == 'Banana Plant' else [12, 33]
            for days_ago in fertilize_dates:
                conn.execute(
                    '''
                    INSERT INTO fertilizer_history (
                        plant_id, application_date, fertilizer_name, npk_ratio, dosage_g, notes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        plant_id,
                        _iso(days_ago),
                        'Balanced Feed' if days_ago == fertilize_dates[0] else 'Slow Release Blend',
                        '10-10-10' if days_ago == fertilize_dates[0] else '5-5-5',
                        12.0 if days_ago == fertilize_dates[0] else 8.0,
                        'Routine feeding',
                    ),
                )

            if plant['name'] == 'Monstera Deliciosa':
                conn.execute(
                    '''
                    INSERT INTO repotting_records (plant_id, repot_date, pot_size_in, root_bound, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (plant_id, _iso(64), 10.0, 1, 'Roots beginning to circle the pot.'),
                )
            elif plant['name'] in {'Banana Plant', 'Tomato Plant'}:
                conn.execute(
                    '''
                    INSERT INTO repotting_records (plant_id, repot_date, pot_size_in, root_bound, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (plant_id, _iso(90), 12.0, 0, 'Recently refreshed soil and container.'),
                )

            growth_series = {
                'Banana Plant': [132.0, 136.0, 140.5, 145.0],
                'Tomato Plant': [38.0, 41.5, 45.0, 49.0],
                'Hibiscus': [58.0, 59.2, 60.3, 61.5],
                'Monstera Deliciosa': [44.0, 46.0, 48.0, 50.5],
                'Sweet Basil': [26.0, 25.4, 24.8, 24.1],
                'Mint': [18.0, 21.0, 24.5, 28.0],
                'Cucumber Vine': [35.0, 38.2, 41.4, 45.0],
                'Snake Plant': [52.0, 52.1, 52.1, 52.2],
                'Succulent Mix': [14.0, 14.1, 14.2, 14.3],
                'Aloe Vera': [19.0, 19.0, 19.1, 19.1],
                'Rose': [40.0, 42.5, 45.0, 47.0],
            }[plant['name']]
            leaf_series = {
                'Banana Plant': [7, 8, 9, 11],
                'Tomato Plant': [18, 20, 22, 24],
                'Hibiscus': [26, 27, 28, 30],
                'Monstera Deliciosa': [9, 10, 11, 12],
                'Sweet Basil': [20, 18, 17, 15],
                'Mint': [24, 28, 33, 37],
                'Cucumber Vine': [14, 16, 18, 21],
                'Snake Plant': [10, 10, 10, 10],
                'Succulent Mix': [16, 16, 17, 17],
                'Aloe Vera': [12, 12, 12, 12],
                'Rose': [34, 35, 36, 37],
            }[plant['name']]
            for offset in range(4):
                conn.execute(
                    '''
                    INSERT INTO growth_logs (
                        plant_id, log_date, height_cm, leaf_count, bloom_count, note
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        plant_id,
                        _iso(28 - offset * 7),
                        growth_series[offset],
                        leaf_series[offset],
                        1 if plant['name'] in {'Hibiscus', 'Rose'} and offset >= 2 else 0,
                        'Weekly growth check',
                    ),
                )

            expenses = [
                (LAST_MONTH_END, 'gardening supplies', 18.50, 'Garden Center', 'Potting mix and labels'),
                (CURRENT_MONTH_DAY, 'gardening supplies', 14.25, 'Home Depot', 'Plant ties and trays'),
                (_iso(3), 'fertilizer', 6.25, 'Garden Center', 'Balanced feed'),
            ]
            for expense_date, category, amount_usd, vendor, note in expenses:
                conn.execute(
                    '''
                    INSERT INTO expenses (
                        plant_id, expense_date, category, amount_usd, vendor, note
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (plant_id, expense_date if isinstance(expense_date, str) else expense_date.isoformat(), category, amount_usd, vendor, note),
                )

            conn.execute(
                '''
                INSERT INTO purchase_logs (
                    plant_id, purchase_date, store, amount_usd, items
                ) VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    plant_id,
                    plant['purchase_date'],
                    'Local Nursery',
                    24.0 + (plant_id % 5) * 6.5,
                    f"{plant['name']} starter plant",
                ),
            )

        conn.executemany(
            '''
            INSERT INTO diagnostics (
                plant_id, diagnosis_date, symptom, severity, likely_cause, recommended_action
            ) VALUES (
                (SELECT id FROM plants WHERE name = ?), ?, ?, ?, ?, ?
            )
            ''',
            [
                ('Tomato Plant', _iso(2), 'yellow leaves with brown spots', 'high', 'possible early blight or bacterial spot', 'remove affected leaves and confirm with a web search'),
                ('Sweet Basil', _iso(3), 'yellowing leaves', 'high', 'overwatering or nutrient imbalance', 'adjust watering and check drainage'),
                ('Cucumber Vine', _iso(1), 'powdery residue on leaves', 'medium', 'powdery mildew pressure', 'prune for airflow and treat early'),
                ('Monstera Deliciosa', _iso(4), 'roots filling the pot', 'medium', 'likely root bound', 'consider repotting into a larger container'),
            ],
        )

        conn.executemany(
            '''
            INSERT INTO shopping_list (item_name, category, status, priority, added_date, source)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            [
                ('neem oil', 'pest control', 'open', 'high', _iso(8), 'seed data'),
                ('peat-free potting soil', 'soil', 'open', 'medium', _iso(9), 'seed data'),
                ('plant ties', 'support', 'open', 'low', _iso(4), 'seed data'),
            ],
        )

        conn.commit()
    finally:
        conn.close()


__all__ = ['connect', 'reset_database', 'setup_database', 'CARE_PROFILES', 'PERSONAL_PLANTS']

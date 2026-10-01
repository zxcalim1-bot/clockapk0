# -*- coding: utf-8 -*-
"""Clock Assistant для Android (Kivy). Офлайн: транслит + решатель + SQLite."""
import os, math, re, sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse
from kivy.clock import Clock as KvClock
from kivy.core.window import Window

Window.clearcolor = (0.06, 0.08, 0.1, 1)

# ---------- БАЗА ДАННЫХ ----------
def db_path():
    d = App.get_running_app().user_data_dir
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "clock_assistant.db")

DB_CON = None
def db_init():
    global DB_CON
    DB_CON = sqlite3.connect(db_path())
    DB_CON.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT, time TEXT, question TEXT, answer TEXT)""")
    DB_CON.commit()

def db_save(q, a):
    DB_CON.execute("INSERT INTO history(time,question,answer) VALUES(?,?,?)",
                   (datetime.now().strftime("%d.%m %H:%M"), q, a))
    DB_CON.commit()

# ---------- ТРАНСЛИТ ----------
T = {'a':'а','b':'б','v':'в','g':'г','d':'д','e':'е','yo':'ё','zh':'ж','z':'з',
     'i':'и','y':'й','k':'к','l':'л','m':'м','n':'н','o':'о','p':'п','r':'р',
     's':'с','t':'т','u':'у','f':'ф','h':'х','c':'ц','ch':'ч','sh':'ш',
     'sch':'щ','yu':'ю','ya':'я',"'":'ь','"':'ъ'}
MULTI = ['sch','ch','sh','zh','yo','ya','yu']

def to_russian(text):
    t = text.lower().strip()
    out, i = [], 0
    while i < len(t):
        for m in MULTI:
            if t.startswith(m, i):
                out.append(T[m]); i += len(m); break
        else:
            ch = t[i]
            out.append(T.get(ch, ch)); i += 1
    return ''.join(out)

# ---------- РЕШАТЕЛЬ ----------
def nums_of(s):
    return [float(x) for x in re.findall(r'-?\d+\.?\d*', s)]

def solve(raw):
    q = to_russian(raw).replace(',', ' ')
    cleaned = re.sub(r'[^0-9+\-*/(). ]', '', q).strip()
    if cleaned and re.search(r'\d', cleaned) and re.search(r'[+\-*/]', cleaned):
        try:
            val = eval(cleaned, {"__builtins__": {}})
            code = "print(%s)\n# вывод: %s" % (cleaned, val)
            ex = "Результат: %s = %s.\nPython считает по приоритету операций." % (cleaned, val)
            return fmt(raw, q, ex, code)
        except Exception:
            pass
    n = nums_of(q)
    ex, code = "", ""
    if 'фибона' in q:
        k = int(n[0]) if n else 10
        seq = [0, 1]
        while len(seq) < k: seq.append(seq[-1] + seq[-2])
        code = "a, b = 0, 1\nfor _ in range(%d):\n    a, b = b, a + b\n    print(a, end=' ')" % k
        ex = "Числа Фибоначчи: каждое = сумме двух предыдущих.\nПервые %d: %s" % (k, seq[:k])
    elif 'факториал' in q:
        k = int(n[0]) if n else 5
        r = math.factorial(k)
        code = "import math\nprint(math.factorial(%d))\n# вывод: %d" % (k, r)
        ex = "%d! = произведение чисел от 1 до %d = %d" % (k, k, r)
    elif 'прост' in q:
        k = int(n[0]) if n else 97
        isp = k > 1 and all(k % i for i in range(2, int(k**0.5) + 1))
        code = ("def is_prime(n):\n    if n < 2: return False\n"
                "    for i in range(2, int(n**0.5)+1):\n"
                "        if n %% i == 0: return False\n    return True\n"
                "print(is_prime(%d))  # %s" % (k, isp))
        ex = "%d — %s. Проверяем делимость только до √n." % (k, "ПРОСТОЕ" if isp else "НЕ простое")
    elif 'сортировк' in q or 'отсортируй' in q:
        arr = sorted(n) if n else [1, 2, 5, 9]
        code = "arr = %s\narr.sort()\nprint(arr)" % (n or [5, 2, 9, 1])
        ex = "Отсортировано: %s\nМетод .sort() — Timsort, O(n log n)." % arr
    elif 'палиндром' in q:
        s = re.sub(r'[^a-zа-я0-9]', '', q.split('палиндром')[-1]) or 'шалаш'
        isp = s == s[::-1]
        code = "s = '%s'\nprint(s == s[::-1])  # %s" % (s, isp)
        ex = "«%s» %s. Срез [::-1] разворачивает строку." % (s, "ПАЛИНДРОМ" if isp else "НЕ палиндром")
    elif 'нод' in q:
        a, b = int(n[0]), int(n[1]) if len(n) > 1 else (48, 36)
        code = "import math\nprint(math.gcd(%d, %d))  # %d" % (a, b, math.gcd(a, b))
        ex = "НОД(%d, %d) = %d. Алгоритм Евклида." % (a, b, math.gcd(a, b))
    elif 'нок' in q:
        a, b = int(n[0]), int(n[1]) if len(n) > 1 else (4, 6)
        r = abs(a*b)//math.gcd(a, b)
        code = "import math\na, b = %d, %d\nprint(abs(a*b)//math.gcd(a, b))  # %d" % (a, b, r)
        ex = "НОК(%d, %d) = %d. Формула: |a×b| / НОД." % (a, b, r)
    elif 'корен' in q:
        v = n[0] if n else 144
        code = "import math\nprint(math.sqrt(%s))  # %s" % (v, math.sqrt(v))
        ex = "√%s = %s" % (v, math.sqrt(v))
    elif 'степен' in q or '^' in raw:
        a, b = (n[0], n[1]) if len(n) > 1 else (2, 10)
        code = "print(%s ** %s)  # %s" % (a, b, a**b)
        ex = "%s^%s = %s. В Python степень — это **, а не ^!" % (a, int(b), a**b)
    elif 'средн' in q and n:
        avg = sum(n)/len(n)
        code = "nums = %s\nprint(sum(nums)/len(nums))  # %s" % (n, avg)
        ex = "Среднее = сумма/количество = %s" % avg
    elif 'таблиц' in q and 'умнож' in q:
        k = int(n[0]) if n else 7
        code = "n = %d\nfor i in range(1, 11):\n    print(f'{n} x {i} = {n*i}')" % k
        ex = "\n".join("%d x %d = %d" % (k, i, k*i) for i in range(1, 11))
    elif 'разверни' in q or 'обратн' in q:
        s = re.sub(r'[^a-zа-я0-9]', '', q) or 'привет'
        code = "s = '%s'\nprint(s[::-1])  # %s" % (s, s[::-1])
        ex = "Разворот строки: %s" % s[::-1]
    else:
        code = "# команды: fibonacchi, faktorial, prostoe chislo, sortirovka,\n# palindrom, nod, nok, koren, stepen, srednee, tablica umnozhenija"
        ex = ("Не распознал. Примеры:\n"
              "fibonacchi 10, faktorial 5, prostoe chislo 97,\n"
              "sortirovka 5 2 9, palindrom шалаш, nod 48 36,\n"
              "koren 144, stepen 2 10, srednee 4 8 15, ili 25 * 4 + 10")
    return fmt(raw, q, ex, code)

def fmt(raw, q, ex, code):
    line = "─" * 30
    ans = ("Вы написали: «%s» → «%s»\n%s\n📖 ОБЪЯСНЕНИЕ:\n%s\n\n%s\n💻 КОД:\n%s\n"
           % (raw, q, line, ex, line, code))
    db_save(raw, ans)
    return ans

# ---------- ЧАСЫ (холст) ----------
class Dial(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(size=self.redraw, pos=self.redraw)
        KvClock.schedule_interval(lambda dt: self.redraw(), 0.3)
    def redraw(self, *a):
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        R = min(self.width, self.height) * 0.42
        with self.canvas:
            Color(0.23, 0.29, 0.36)
            Line(circle=(cx, cy, R), width=2)
            now = datetime.now()
            h = (now.hour % 12) * 30 + now.minute * 0.5
            m = now.minute * 6 + now.second * 0.1
            s = now.second * 6
            for ang, ln, col, w in [(h, R*0.5, (0.91,0.7,0.23,1), 4),
                                    (m, R*0.72, (0.85,0.9,0.95,1), 3),
                                    (s, R*0.85, (0.88,0.33,0.33,1), 1.5)]:
                a = math.radians(ang - 90)
                Color(*col)
                Line(points=[cx, cy, cx + ln*math.cos(a), cy + ln*math.sin(a)], width=w)
            Color(0.91, 0.7, 0.23)
            Ellipse(pos=(cx-5, cy-5), size=(10, 10))

# ---------- ЭКРАН ----------
PRESETS = ["fibonacchi 10","faktorial 5","prostoe chislo 97","sortirovka 5 2 9 1",
           "palindrom шалаш","nod 48 36","koren 144","stepen 2 10","srednee 4 8 15",
           "tablica umnozhenija 7","razverni privet","25 * 4 + 10"]

class Root(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation='vertical', padding=8, spacing=6, **kw)
        dial_area = FloatLayout(size_hint_y=0.45)
        dial_area.add_widget(Dial())
        # 12 кнопок по кругу, как цифры часов
        for i, p in enumerate(PRESETS):
            ang = math.radians(i * 30 - 90)
            b = Button(text=str(i + 1), size_hint=(None, None), size=(44, 44),
                       background_color=(0.15, 0.35, 0.6, 1),
                       on_press=lambda btn, txt=p: self.set_input(txt))
            b.bind(pos=lambda inst, v: None)
            dial_area.add_widget(b)
            b.center_x_hint = 0.5 + 0.42 * math.cos(ang)
            b.center_y_hint = 0.5 + 0.42 * math.sin(ang)
            b.pos_hint = {'center_x': b.center_x_hint, 'center_y': b.center_y_hint}
        self.add_widget(dial_area)

        self.out = Label(text="⏰ Clock Assistant готов!\nПишите английскими или русскими буквами.\n",
                         size_hint_y=None, color=(0.85, 0.92, 1, 1),
                         font_size='13sp', halign='left', valign='top',
                         text_size=(Window.width - 30, None))
        self.out.bind(texture_size=self.out.setter('size'))
        sv = ScrollView()
        sv.add_widget(self.out)
        self.add_widget(sv)

        row = BoxLayout(size_hint_y=0.12, spacing=6)
        self.inp = TextInput(hint_text="задача: fibonacchi 10", multiline=False,
                             background_color=(0.14, 0.17, 0.22, 1),
                             foreground_color=(1, 1, 1, 1), font_size='15sp')
        self.inp.bind(on_text_validate=lambda inst: self.ask())
        btn = Button(text="Решить", size_hint_x=0.3,
                     background_color=(0.18, 0.49, 0.86, 1))
        btn.bind(on_press=lambda inst: self.ask())
        row.add_widget(self.inp)
        row.add_widget(btn)
        self.add_widget(row)

    def set_input(self, txt):
        self.inp.text = txt

    def ask(self):
        q = self.inp.text.strip()
        if not q:
            return
        self.inp.text = ""
        try:
            ans = solve(q)
        except Exception as ex:
            ans = "Ошибка: %s" % ex
        self.out.text += ans + "\n" + "=" * 30 + "\n"

class ClockApp(App):
    def build(self):
        db_init()
        self.title = "Clock Assistant"
        return Root()

if __name__ == "__main__":
    ClockApp().run()

# web.py

from flask import Flask, render_template_string
from db import Session, Aquarium, Measurement
from parameters import PARAMETERS

app = Flask(__name__)

HTML = """
<!doctype html>
<title>Журнал аквариума</title>
<table border=1 cellpadding=6>
<tr><th>ID</th><th>Аква</th><th>Параметр</th><th>Значение</th><th>Время</th></tr>
{% for m in ms %}
<tr style="background:{% if m.out %}#fdd{% else %}#fff{% endif %}">
<td>{{m.id}}</td><td>{{m.aq}}</td><td>{{m.param}}</td>
<td>{{m.value}}</td><td>{{m.created_at}}</td>
</tr>
{% endfor %}
</table>
"""

@app.route("/")
def index():
    session = Session()
    ms = session.query(Measurement).order_by(Measurement.created_at.desc()).limit(30).all()
    data = []
    for m in ms:
        out = False
        n = PARAMETERS.get(m.param)
        if n and (m.value<n["min"] or m.value>n["max"]): out=True
        data.append(dict(
            id=m.id, aq=session.get(Aquarium,m.aquarium_id).name,
            param=m.param, value=m.value,
            created_at=m.created_at.strftime("%d.%m %H:%M"), out=out
        ))
    return render_template_string(HTML, ms=data)
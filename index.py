from flask import Flask, request, redirect, url_for, session, abort, render_template_string
import json, os, re
from math import ceil
from slugify import slugify  # pip install python-slugify

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

VIDEO_FILE = 'videos.json'
ADMIN_PASSWORD = 'helena'
VIDEOS_POR_PAGINA = 10

# Helpers
def carregar_videos():
    if os.path.exists(VIDEO_FILE):
        with open(VIDEO_FILE, 'r') as f:
            return json.load(f)
    return []

def salvar_videos(videos):
    with open(VIDEO_FILE, 'w') as f:
        json.dump(videos, f, indent=2)

def gerar_slug(titulo):
    return slugify(titulo)

def render_page(content, **kwargs):
    base_html = '''
    <!doctype html>
    <html lang="pt-br">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{{ title }}</title>
        <meta name="description" content="{{ description }}">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container py-5">
            {{ content | safe }}
        </div>
    </body>
    </html>
    '''
    return render_template_string(base_html, content=content, **kwargs)

# Página principal com paginação
@app.route('/')
@app.route('/page/<int:pagina>')
def index(pagina=1):
    videos = carregar_videos()
    total = len(videos)
    total_paginas = ceil(total / VIDEOS_POR_PAGINA)
    inicio = (pagina - 1) * VIDEOS_POR_PAGINA
    fim = inicio + VIDEOS_POR_PAGINA
    videos_pagina = videos[inicio:fim]

    content = '''
    <h1 class="text-center mb-4">🎬 Galeria de Vídeos</h1>
    <div class="row">
    {% for video in videos %}
        <div class="col-md-6 mb-4">
            <div class="card h-100">
                <div class="card-body d-flex flex-column">
                    <h5>{{ video.title }}</h5>
                    <div class="ratio ratio-16x9 mb-3">
                        <iframe src="{{ video.url }}" frameborder="0" allowfullscreen></iframe>
                    </div>
                    <p class="flex-grow-1">{{ video.description }}</p>
                    <a href="{{ url_for('ver_video', slug=video.slug) }}" class="btn btn-sm btn-outline-primary mt-auto">Ver Página</a>
                </div>
            </div>
        </div>
    {% endfor %}
    </div>
    {% if total_paginas > 1 %}
    <nav>
        <ul class="pagination justify-content-center">
        {% for p in range(1, total_paginas + 1) %}
            <li class="page-item {% if p == pagina %}active{% endif %}">
                <a class="page-link" href="{{ url_for('index', pagina=p) }}">{{ p }}</a>
            </li>
        {% endfor %}
        </ul>
    </nav>
    {% endif %}
    <div class="text-center mt-4">
        <a href="{{ url_for('login') }}" class="btn btn-primary">Login Admin</a>
    </div>
    '''
    return render_page(render_template_string(content, videos=videos_pagina, pagina=pagina, total_paginas=total_paginas),
                       title="Galeria de Vídeos", description="Lista de vídeos")

# Página de vídeo individual
@app.route('/video/<slug>')
def ver_video(slug):
    videos = carregar_videos()
    for video in videos:
        if video.get('slug') == slug:
            content = f'''
            <h1>{video["title"]}</h1>
            <iframe class="w-100 mb-3" height="400" src="{video["url"]}" frameborder="0" allowfullscreen></iframe>
            <p>{video["description"]}</p>
            <a href="{{{{ url_for('index') }}}}" class="btn btn-secondary">Voltar</a>
            '''
            return render_page(content, title=video["title"], description=video["description"])
    return abort(404)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('senha') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        return "Senha incorreta", 403

    content = '''
    <h1>🔐 Login</h1>
    <form method="post">
        <div class="mb-3">
            <label class="form-label">Senha</label>
            <input type="password" name="senha" class="form-control" required>
        </div>
        <button class="btn btn-success" type="submit">Entrar</button>
    </form>
    '''
    return render_page(content, title="Login", description="Área restrita")

# Admin
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))

    videos = carregar_videos()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        video_id = request.form.get('video_id', '').strip()
        description = request.form.get('description', '').strip()

        if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
            return "ID do vídeo inválido", 400

        url = f"https://www.youtube.com/embed/{video_id}"
        slug = gerar_slug(title)
        if any(v.get("slug") == slug for v in videos):
            slug += f"-{len(videos)}"

        videos.append({
            "title": title,
            "url": url,
            "description": description,
            "slug": slug
        })
        salvar_videos(videos)
        return redirect(url_for('admin'))

    content = '''
    <h1>📥 Adicionar Vídeo</h1>
    <form method="post">
        <input name="title" placeholder="Título" class="form-control mb-2" required>
        <input name="video_id" placeholder="ID do YouTube (ex: dQw4w9WgXcQ)" class="form-control mb-2" required>
        <textarea name="description" placeholder="Descrição" class="form-control mb-3" required></textarea>
        <button class="btn btn-primary">Adicionar</button>
        <a href="{{ url_for('logout') }}" class="btn btn-outline-secondary ms-2">Sair</a>
    </form>
    <h2 class="mt-4">Vídeos Existentes</h2>
    <ul class="list-group">
    {% for v in videos %}
        <li class="list-group-item">
            <strong>{{ v.title }}</strong><br>
            <small>{{ v.url }}</small><br>
            <code>{{ url_for('ver_video', slug=v.slug) }}</code>
        </li>
    {% endfor %}
    </ul>
    '''
    return render_page(render_template_string(content, videos=videos), title="Admin", description="Gerenciar vídeos")

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# Para rodar no Replit
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

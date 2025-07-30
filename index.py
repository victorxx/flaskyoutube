from flask import Flask, request, redirect, url_for, session, abort, render_template_string
import json
import os
import re
from math import ceil
from slugify import slugify  # pip install python-slugify

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

VIDEO_FILE = 'videos.json'
ADMIN_PASSWORD = 'helena'
VIDEOS_POR_PAGINA = 10

# --- Funções auxiliares ---

def carregar_videos():
    if os.path.exists(VIDEO_FILE):
        with open(VIDEO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_videos(videos):
    with open(VIDEO_FILE, 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=4, ensure_ascii=False)

def gerar_slug(titulo):
    return slugify(titulo)

# --- Layout base com Bootstrap ---

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

# --- Página principal com paginação e propaganda no topo ---

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
    <h1 class="mb-4 text-center">🎬 Galeria de Vídeos</h1>

    <!-- Propaganda única no topo da página -->
    <div class="mb-4">
      <div class="card border-warning">
        <div class="card-header bg-warning text-dark">
          📢 Publicidade
        </div>
        <div class="card-body p-0">
          <iframe 
              src="https://espiritosantoes-com-brprincipal.pages.dev/" 
              width="100%" 
              height="300" 
              style="border: none;"
              title="Publicidade">
          </iframe>
        </div>
      </div>
    </div>

    <div class="row">
    {% for video in videos %}
      <div class="col-md-6 mb-4">
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <h5 class="card-title">{{ video.title }}</h5>
            <div class="ratio ratio-16x9 mb-3">
              <iframe src="{{ video.url }}" frameborder="0" allowfullscreen></iframe>
            </div>
            <p class="card-text flex-grow-1">{{ video.description }}</p>
            <a href="{{ url_for('ver_video', slug=video.slug) }}" class="btn btn-sm btn-outline-primary mt-auto">Ver Página</a>
          </div>
        </div>
      </div>
    {% endfor %}
    </div>

    {% if total_paginas > 1 %}
    <nav aria-label="Navegação de página">
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
      <a class="btn btn-primary" href="{{ url_for('login') }}">Login Admin</a>
    </div>
    '''
    return render_page(render_template_string(content, videos=videos_pagina, pagina=pagina, total_paginas=total_paginas),
                       title="Galeria de Vídeos",
                       description="Vídeos paginados com descrição e SEO")

# --- Página individual do vídeo com propaganda no topo ---

@app.route('/video/<slug>')
def ver_video(slug):
    videos = carregar_videos()
    for video in videos:
        if video.get('slug') == slug:
            content = f'''
            <h1>{video["title"]}</h1>

            <!-- Propaganda no topo -->
            <div class="mb-4">
              <div class="card border-warning">
                <div class="card-header bg-warning text-dark">
                  📢 Publicidade
                </div>
                <div class="card-body p-0">
                  <iframe 
                      src="https://espiritosantoes-com-brprincipal.pages.dev/" 
                      width="100%" 
                      height="200" 
                      style="border: none;"
                      title="Publicidade">
                  </iframe>
                </div>
              </div>
            </div>

            <iframe class="w-100 mb-3" height="400" src="{video["url"]}" frameborder="0" allowfullscreen></iframe>
            <p>{video["description"]}</p>
            <a href="{{{{ url_for('index') }}}}" class="btn btn-secondary">Voltar</a>
            '''
            return render_page(content, title=video["title"], description=video["description"])
    return abort(404)

# --- Login admin ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return "Senha incorreta", 403

    content = '''
    <h1>🔐 Login do Administrador</h1>
    <form method="post" class="mt-4">
        <div class="mb-3">
            <label class="form-label">Senha</label>
            <input type="password" name="senha" class="form-control" required>
        </div>
        <button type="submit" class="btn btn-success">Entrar</button>
    </form>
    '''
    return render_page(content, title="Login", description="Área do administrador")

# --- Painel admin para adicionar vídeos ---

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin'):
        return redirect(url_for('login'))

    videos = carregar_videos()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        video_id = request.form.get('video_id', '').strip()
        description = request.form.get('description', '').strip()

        # Validar ID do YouTube (11 caracteres alfanum + "-" ou "_")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
            return "Erro: ID do vídeo inválido", 400

        url = f"https://www.youtube.com/embed/{video_id}"
        slug = gerar_slug(title)

        # Evitar slugs repetidos
        if any(v.get("slug") == slug for v in videos):
            slug += f"-{len(videos)}"

        videos.append({
            "title": title,
            "url": url,
            "description": description,
            "slug": slug,
            "admin": True
        })
        salvar_videos(videos)
        return redirect(url_for('admin'))

    content = '''
    <h1>📥 Adicionar Novo Vídeo</h1>
    <form method="post" class="mb-5">
        <div class="mb-3">
            <label class="form-label">Título</label>
            <input type="text" name="title" class="form-control" required>
        </div>
        <div class="mb-3">
            <label class="form-label">ID do vídeo (YouTube)</label>
            <input type="text" name="video_id" class="form-control" required placeholder="Ex: dQw4w9WgXcQ">
        </div>
        <div class="mb-3">
            <label class="form-label">Descrição</label>
            <textarea name="description" class="form-control" rows="3" required></textarea>
        </div>
        <button type="submit" class="btn btn-primary">Adicionar</button>
        <a href="{{ url_for('logout') }}" class="btn btn-outline-secondary ms-2">Sair</a>
    </form>

    <h2>📄 Vídeos Existentes</h2>
    <ul class="list-group">
    {% for video in videos %}
        <li class="list-group-item">
            <strong>{{ video.title }}</strong><br>
            <small>{{ video.url }}</small><br>
            <em>{{ video.description }}</em><br>
            <code>{{ url_for('ver_video', slug=video.slug) }}</code>
        </li>
    {% endfor %}
    </ul>
    '''
    return render_page(render_template_string(content, videos=videos), title="Administração", description="Painel Admin")

# --- Logout ---

@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# --- Run app ---

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template_string, send_file, jsonify, request
import requests
import random
import io
import zipfile
import re
import string

app = Flask(__name__)

def get_cats_content(count=10, after=None):
    content = []
    headers = {'User-agent': 'CatApp 1.0'}
    url = f'https://www.reddit.com/r/cats/.json?limit=100&after={after}' if after else 'https://www.reddit.com/r/cats/.json?limit=100'

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        posts = data['data']['children']
        for post in posts:
            post_data = post['data']
            if post_data['is_video']:
                if 'reddit_video' in post_data['media']:
                    content.append({
                        'type': 'video',
                        'url': post_data['media']['reddit_video']['fallback_url'],
                        'title': post_data['title']
                    })
            elif 'url_overridden_by_dest' in post_data and re.search(r'\.(jpg|jpeg|png|gif)$', post_data['url_overridden_by_dest']):
                content.append({
                    'type': 'image',
                    'url': post_data['url_overridden_by_dest'],
                    'title': post_data['title']
                })
            if len(content) == count:
                break
        
        new_after = data['data']['after']
        return content, new_after
    else:
        return [], None

def sanitize_filename(filename):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    sanitized = ''.join(c for c in filename if c in valid_chars)
    return sanitized[:200]

@app.route('/')
def index():
    cats_content, after = get_cats_content(10)
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>r/cats Content Display</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f0f0f0; }
            h1 { text-align: center; color: #333; }
            .content-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .content-container { background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden; }
            .content-media { width: 100%; height: 300px; object-fit: cover; }
            .content-title { padding: 10px; margin: 0; font-size: 14px; text-align: center; }
            .button-container { text-align: center; margin-top: 20px; }
            button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin: 0 10px; }
            .download-btn { background-color: #008CBA; }
            .reload-btn { background-color: #f44336; }
        </style>
    </head>
    <body>
        <h1>r/cats Content Display</h1>
        <div id="content-grid" class="content-grid">
            {% for item in cats_content %}
                <div class="content-container">
                    {% if item.type == 'video' %}
                        <video class="content-media" controls>
                            <source src="{{ item.url }}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    {% else %}
                        <img src="{{ item.url }}" alt="{{ item.title }}" class="content-media">
                    {% endif %}
                    <p class="content-title">{{ item.title }}</p>
                </div>
            {% endfor %}
        </div>
        <div class="button-container">
            <a href="{{ url_for('download_content') }}">
                <button class="download-btn">Download All Content</button>
            </a>
            <button onclick="reloadContent()" class="reload-btn">Reload Content</button>
        </div>

        <script>
        let after = "{{ after }}";
        function reloadContent() {
            fetch(`/get-content?after=${after}`)
                .then(response => response.json())
                .then(data => {
                    const contentGrid = document.getElementById('content-grid');
                    contentGrid.innerHTML = '';
                    data.content.forEach(item => {
                        const contentContainer = document.createElement('div');
                        contentContainer.className = 'content-container';
                        if (item.type === 'video') {
                            contentContainer.innerHTML = `
                                <video class="content-media" controls>
                                    <source src="${item.url}" type="video/mp4">
                                    Your browser does not support the video tag.
                                </video>
                                <p class="content-title">${item.title}</p>
                            `;
                        } else {
                            contentContainer.innerHTML = `
                                <img src="${item.url}" alt="${item.title}" class="content-media">
                                <p class="content-title">${item.title}</p>
                            `;
                        }
                        contentGrid.appendChild(contentContainer);
                    });
                    after = data.after;
                })
                .catch(error => console.error('Error:', error));
        }
        </script>
    </body>
    </html>
    ''', cats_content=cats_content, after=after)

@app.route('/get-content')
def get_content():
    after = request.args.get('after')
    cats_content, new_after = get_cats_content(10, after)
    return jsonify({'content': cats_content, 'after': new_after})

@app.route('/download')
def download_content():
    cats_content, _ = get_cats_content(10)
    
    # Create a ZIP file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for i, item in enumerate(cats_content):
            response = requests.get(item['url'])
            if response.status_code == 200:
                file_ext = 'mp4' if item['type'] == 'video' else item['url'].split('.')[-1]
                sanitized_title = sanitize_filename(item['title'])
                filename = f"{i+1}_{sanitized_title}.{file_ext}"
                zf.writestr(filename, response.content)
    
    memory_file.seek(0)
    return send_file(memory_file, mimetype='application/zip', as_attachment=True, download_name='r_cats_content.zip')

if __name__ == '__main__':
    app.run(debug=True)
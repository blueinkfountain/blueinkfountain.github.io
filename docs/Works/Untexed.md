---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% comment %} 
  루트의 /untexed/ 폴더를 검색하도록 변경 
{% endcomment %}
{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" | sort: "path" %}

{% if pdf_files.size == 0 %}
  <p style="color: #666;">PDF 파일을 찾을 수 없습니다. (대상 폴더: /untexed/)</p>
  <p style="font-size: 0.8em; color: #999;">Tip: 폴더 이름이 정확히 소문자 untexed인지 확인하고, 파일을 넣은 후 서버를 재시작해 보세요.</p>
{% endif %}

{% assign last_dir = "" %}

<ul class="file-tree">
{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    
    {% comment %} 
      경로 분석: 
      /untexed/Algebra/test.pdf -> ["", "untexed", "Algebra", "test.pdf"] (크기 4)
      /untexed/test.pdf -> ["", "untexed", "test.pdf"] (크기 3)
    {% endcomment %}
    {% assign path_parts = file.path | split: "/" %}
    
    {% if path_parts.size == 4 %}
      {% comment %} 하위 폴더가 있는 경우 {% endcomment %}
      {% assign current_dir = path_parts[2] %}
      
      {% if current_dir != last_dir %}
        {% if last_dir != "" %}</ul></li>{% endif %}
        <li class="folder-item"><strong>📁 {{ current_dir | replace: "_", " " | capitalize }}</strong>
        <ul>
        {% assign last_dir = current_dir %}
      {% endif %}
      
      <li>
        <a href="{{ file.path | relative_url }}" target="_blank">📄 {{ file.basename }}</a>
      </li>
      
    {% elsif path_parts.size == 3 %}
      {% comment %} untexed 바로 아래에 파일이 있는 경우 {% endcomment %}
      {% if last_dir != "" %}
        </ul></li>
        {% assign last_dir = "" %}
      {% endif %}
      <li>
        <a href="{{ file.path | relative_url }}" target="_blank">📄 {{ file.basename }}</a>
      </li>
    {% endif %}

  {% endif %}
{% endfor %}
{% if last_dir != "" %}</ul></li>{% endif %}
</ul>

<style>
  .file-tree { list-style-type: none; padding-left: 0; }
  .file-tree ul { list-style-type: none; padding-left: 25px; border-left: 1px solid #eee; margin: 5px 0 15px 5px; }
  .file-tree li { margin: 8px 0; font-size: 15px; }
  .file-tree .folder-item { margin-top: 15px; }
  .file-tree strong { color: #2c3e50; font-size: 16px; }
  .file-tree a { text-decoration: none; color: #007bff; }
  .file-tree a:hover { text-decoration: underline; color: #0056b3; }
</style>
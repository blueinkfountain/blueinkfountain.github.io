---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/math-blog/untexed/untexed/'" | sort: "path" %}

{% assign last_dir = "" %}

<ul>
{% for file in pdf_files %}
  {% if file.extname == ".pdf" %}
    {% comment %} 파일 경로에서 폴더명만 추출 {% endcomment %}
    {% assign parts = file.path | split: "/" %}
    {% assign folder_index = parts.size | minus: 2 %}
    {% assign current_dir = parts[folder_index] %}

    {% if current_dir != last_dir and current_dir != "untexed" %}
      {% if last_dir != "" %}</ul></li>{% endif %}
      <li><strong>📁 {{ current_dir | capitalize }}</strong>
      <ul>
      {% assign last_dir = current_dir %}
    {% endif %}

    <li>
      <a href="{{ file.path | relative_url }}" target="_blank">{{ file.basename }}</a>
    </li>
  {% endif %}
{% endfor %}
</ul>
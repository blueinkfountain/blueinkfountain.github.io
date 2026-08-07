---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% comment %} 
  1. /untexed/ 폴더 안의 모든 PDF를 가져와서 경로순으로 정렬합니다. 
{% endcomment %}
{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" | sort: "path" %}

<div class="file-tree-container">
{% assign last_path_parts = "" | split: "/" %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    
    {% comment %} 
      경로 예시: /untexed/Analysis/3. Analysis on Manifold/Chapter1.pdf 
      parts: ["", "untexed", "Analysis", "3. Analysis on Manifold", "Chapter1.pdf"]
    {% endcomment %}
    {% assign current_path_parts = file.path | split: "/" %}
    {% assign file_name = current_path_parts | last %}
    
    {% comment %} 실제 폴더 부분만 추출 (0, 1번 인덱스는 "", "untexed" 이므로 2번부터 시작) {% endcomment %}
    {% assign current_folder_parts = "" | split: "/" %}
    {% for part in current_path_parts %}
      {% if forloop.index > 2 and forloop.last == false %}
        {% assign current_folder_parts = current_folder_parts | push: part %}
      {% endif %}
    {% endfor %}

    {% comment %} 이전 파일과 비교하여 폴더가 바뀌었는지 확인 {% endcomment %}
    <div class="folder-breadcrumb">
      {% assign breadcrumb = "" %}
      {% for part in current_folder_parts %}
        {% if forloop.first %}
          {% assign breadcrumb = part %}
        {% else %}
          {% assign breadcrumb = breadcrumb | append: " &rsaquo; " | append: part %}
        {% endif %}
      {% endfor %}
      
      {% capture current_folder_str %}{{ breadcrumb }}{% endcapture %}
      {% if current_folder_str != last_folder_str %}
        <h3 class="folder-title">📁 {{ current_folder_str | replace: "_", " " }}</h3>
        {% assign last_folder_str = current_folder_str %}
      {% endif %}
    </div>

    <ul class="pdf-list">
      <li class="pdf-item">
        <a href="{{ file.path | relative_url }}" target="_blank" class="pdf-link">
          <span class="icon">📄</span>
          <span class="name">{{ file.basename }}</span>
        </a>
      </li>
    </ul>

  {% endif %}
{% endfor %}
</div>

<style>
  .file-tree-container { font-family: sans-serif; max-width: 900px; margin: 20px 0; }
  
  /* 폴더 경로 표시 (Breadcrumb 스타일) */
  .folder-title {
    background-color: #f8f9fa;
    padding: 10px 15px;
    border-radius: 6px;
    border-left: 4px solid #007bff;
    font-size: 16px;
    margin-top: 30px;
    margin-bottom: 10px;
    color: #333;
  }
  
  /* PDF 리스트 스타일 */
  .pdf-list { list-style: none; padding-left: 10px; margin: 0; }
  .pdf-item { margin: 8px 0; border-bottom: 1px solid #f0f0f0; padding-bottom: 5px; }
  
  .pdf-link {
    display: flex;
    align-items: center;
    text-decoration: none;
    color: #007bff;
    transition: 0.2s;
  }
  
  .pdf-link:hover { color: #0056b3; transform: translateX(5px); }
  .pdf-link .icon { margin-right: 10px; font-size: 18px; }
  .pdf-link .name { font-size: 15px; }

  /* 첫 번째 폴더 위쪽 여백 조절 */
  .folder-breadcrumb:first-child .folder-title { margin-top: 10px; }
</style>
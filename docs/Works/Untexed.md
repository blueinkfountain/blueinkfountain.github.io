---
layout: default
title: UnTexed
parent: Works
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" | sort: "path" %}

<div class="file-tree-container">
{% assign last_folder_str = "" %}
{% assign first_folder = true %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    
    {% assign current_path_parts = file.path | split: "/" %}
    
    {% comment %} 폴더 경로 추출 (untexed 이후부터 파일명 이전까지) {% endcomment %}
    {% assign folder_parts = "" | split: "/" %}
    {% for part in current_path_parts %}
      {% if forloop.index > 2 and forloop.last == false %}
        {% assign folder_parts = folder_parts | push: part %}
      {% endif %}
    {% endfor %}
    
    {% capture current_folder_str %}{{ folder_parts | join: " › " }}{% endcapture %}
    {% if current_folder_str == "" %}{% assign current_folder_str = "General / Root" %}{% endif %}

    {% comment %} 새로운 폴더가 시작될 때 details 태그를 열어줌 {% endcomment %}
    {% if current_folder_str != last_folder_str %}
      {% if first_folder == false %}
        </ul>
        </details>
      {% endif %}
      
      <details class="folder-group">
        <summary class="folder-header">
          <span class="folder-icon">📁</span>
          <span class="folder-name">{{ current_folder_str | replace: "_", " " }}</span>
          <span class="file-count">
            {% comment %} 해당 폴더 내 파일 개수를 미리 계산하긴 어려우므로 디자인적 요소로만 배치 {% endcomment %}
          </span>
        </summary>
        <ul class="pdf-list">
      {% assign last_folder_str = current_folder_str %}
      {% assign first_folder = false %}
    {% endif %}

    <li class="pdf-item">
      <a href="{{ file.path | relative_url }}" target="_blank" class="pdf-link">
        <span class="icon">📄</span>
        <span class="name">{{ file.basename }}</span>
      </a>
    </li>

  {% endif %}
{% endfor %}

{% if first_folder == false %}
    </ul>
  </details>
{% endif %}
</div>

<style>
  .file-tree-container { 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 100%;
    margin: 20px 0;
  }

  /* 폴더 그룹 스타일 */
  .folder-group {
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    margin-bottom: 8px;
    background-color: #fff;
    overflow: hidden;
  }

  /* 폴더 제목(클릭 영역) 스타일 */
  .folder-header {
    padding: 12px 16px;
    background-color: #f6f8fa;
    cursor: pointer;
    list-style: none; /* 기본 화살표 숨기기 */
    display: flex;
    align-items: center;
    font-weight: 600;
    color: #24292e;
    transition: background-color 0.2s;
  }

  .folder-header:hover {
    background-color: #f1f3f5;
  }

  /* HTML 기본 화살표 커스텀 (필요시) */
  .folder-header::-webkit-details-marker {
    display: none;
  }

  .folder-icon {
    margin-right: 10px;
    font-size: 1.1em;
  }

  .folder-name {
    flex-grow: 1;
    font-size: 15px;
  }

  /* 열렸을 때 스타일 */
  .folder-group[open] .folder-header {
    border-bottom: 1px solid #e1e4e8;
    background-color: #eaf5ff;
    color: #0366d6;
  }

  /* PDF 리스트 스타일 */
  .pdf-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .pdf-item {
    border-bottom: 1px solid #f6f8fa;
  }

  .pdf-item:last-child {
    border-bottom: none;
  }

  .pdf-link {
    display: flex;
    align-items: center;
    padding: 10px 20px 10px 45px;
    text-decoration: none;
    color: #444;
    font-size: 14px;
    transition: background-color 0.2s;
  }

  .pdf-link:hover {
    background-color: #f8f9fa;
    color: #007bff;
  }

  .pdf-link .icon {
    margin-right: 12px;
    opacity: 0.7;
  }

  .pdf-link .name {
    word-break: break-all;
  }
</style>
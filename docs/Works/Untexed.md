---
layout: default
title: Handwritten notes
has_children: true
nav_order: 3
---

# Handwritten notes yet to be TeXed.

{% assign pdf_files = site.static_files
  | where_exp: "item", "item.path contains '/untexed/'"
  | sort: "path"
%}


{%- comment -%}
=========================================================
날짜 목록 수집

예:
  /untexed/260813/Algebra/1. Linear Algebra/foo.pdf

path_parts:
  [0] = ""
  [1] = "untexed"
  [2] = "260813"
  [3] = "Algebra"
  [4] = "1. Linear Algebra"
  [5] = "foo.pdf"
=========================================================
{%- endcomment -%}

{% assign dates = "" | split: "" %}

{% for file in pdf_files %}

  {% if file.extname == ".pdf" or file.extname == ".PDF" %}

    {% assign path_parts = file.path | split: "/" %}
    {% assign file_date = path_parts[2] %}

    {% unless dates contains file_date %}
      {% assign dates = dates | push: file_date %}
    {% endunless %}

  {% endif %}

{% endfor %}


{%- comment -%}
날짜를 최신순으로 정렬
{%- endcomment -%}

{% assign dates = dates | sort | reverse %}
{% assign latest_date = dates[0] %}



<div class="academic-tree-container">


  {%- comment -%}
  =========================================================
  최신 버전
  =========================================================
  {%- endcomment -%}


  {% assign last_folder_str = "" %}
  {% assign last_subject = "" %}
  {% assign first_folder = true %}


  {% for file in pdf_files %}


    {% if file.extname == ".pdf" or file.extname == ".PDF" %}


      {% assign current_path_parts = file.path | split: "/" %}
      {% assign file_date = current_path_parts[2] %}


      {% if file_date == latest_date %}



        {%- comment -%}
        =====================================================
        최상위 Subject

        /untexed/260813/Algebra/...
        -> Algebra

        /untexed/260813/Analysis/...
        -> Analysis

        날짜 폴더 바로 아래의 PDF
        -> General
        =====================================================
        {%- endcomment -%}

        {% if current_path_parts.size > 4 %}

          {% assign current_subject = current_path_parts[3] %}

        {% else %}

          {% assign current_subject = "General" %}

        {% endif %}




        {%- comment -%}
        =====================================================
        실제 폴더 경로

        /untexed/260813/Algebra/1. Linear Algebra/foo.pdf

        -> Algebra / 1. Linear Algebra
        =====================================================
        {%- endcomment -%}


        {% assign folder_parts = "" | split: "" %}


        {% for part in current_path_parts %}

          {% if forloop.index > 3 and forloop.last == false %}

            {% assign folder_parts = folder_parts | push: part %}

          {% endif %}

        {% endfor %}



        {% capture current_folder_str %}

          {{ folder_parts | join: " / " }}

        {% endcapture %}


        {% assign current_folder_str = current_folder_str | strip %}



        {% if current_folder_str == "" %}

          {% assign current_folder_str = "General" %}

        {% endif %}




        {%- comment -%}
        =====================================================
        새로운 폴더가 시작될 때
        =====================================================
        {%- endcomment -%}


        {% if current_folder_str != last_folder_str %}



          {%- comment -%}
          이전 폴더 닫기
          {%- endcomment -%}

          {% if first_folder == false %}

            </ul>
            </details>

          {% endif %}




          {%- comment -%}
          Subject가 변경되면 구분 영역 출력
          {%- endcomment -%}

          {% if current_subject != last_subject %}


            <div class="subject-divider">

              <div class="subject-title">

                {{ current_subject | replace: "_", " " }}

              </div>

            </div>


            {% assign last_subject = current_subject %}


          {% endif %}




          <details class="academic-folder">


            <summary class="folder-summary">

              <span class="folder-label">

                {{ current_folder_str | replace: "_", " " }}

              </span>

            </summary>


            <ul class="file-list">



          {% assign last_folder_str = current_folder_str %}
          {% assign first_folder = false %}


        {% endif %}




        <li class="file-item">


          <a
            href="{{ file.path | relative_url }}"
            target="_blank"
            class="file-link"
          >

            {{ file.basename }}

          </a>


        </li>



      {% endif %}


    {% endif %}


  {% endfor %}




  {%- comment -%}
  최신 버전 마지막 폴더 닫기
  {%- endcomment -%}

  {% if first_folder == false %}

    </ul>
    </details>

  {% endif %}





  {%- comment -%}
  =========================================================
  최신 버전 Record

  최신 버전에서는:
  파일 목록 → Record

  Record는 기본적으로 닫혀 있다.
  =========================================================
  {%- endcomment -%}


  {% assign latest_record = site.data.untexed_records[latest_date] %}


  {% if latest_record %}


    {% assign has_added = latest_record.added.size %}
    {% assign has_modified = latest_record.modified.size %}
    {% assign has_moved = latest_record.moved_renamed.size %}
    {% assign has_deleted = latest_record.deleted.size %}



    {% if has_added > 0 or has_modified > 0 or has_moved > 0 or has_deleted > 0 %}



      <details class="change-record latest-record">


        <summary class="record-summary">

          Record

        </summary>



        <div class="record-content">



          {%- comment -%}
          Added
          {%- endcomment -%}

          {% if latest_record.added.size > 0 %}


            <div class="record-section">


              <div class="record-label">

                Added

              </div>


              <ul class="record-list">


                {% for path in latest_record.added %}

                  <li class="record-added">

                    {{ path }}

                  </li>

                {% endfor %}


              </ul>


            </div>


          {% endif %}





          {%- comment -%}
          Modified
          {%- endcomment -%}

          {% if latest_record.modified.size > 0 %}


            <div class="record-section">


              <div class="record-label">

                Modified

              </div>


              <ul class="record-list">


                {% for path in latest_record.modified %}

                  <li class="record-modified">

                    {{ path }}

                  </li>

                {% endfor %}


              </ul>


            </div>


          {% endif %}





          {%- comment -%}
          Moved / Renamed
          {%- endcomment -%}

          {% if latest_record.moved_renamed.size > 0 %}


            <div class="record-section">


              <div class="record-label">

                Moved / Renamed

              </div>


              <ul class="record-list">


                {% for move in latest_record.moved_renamed %}


                  <li class="record-moved">


                    <span class="record-move-from">

                      {{ move.from }}

                    </span>


                    <span class="record-arrow">

                      →

                    </span>


                    <span class="record-move-to">

                      {{ move.to }}

                    </span>


                  </li>


                {% endfor %}


              </ul>


            </div>


          {% endif %}





          {%- comment -%}
          Removed
          {%- endcomment -%}

          {% if latest_record.deleted.size > 0 %}


            <div class="record-section">


              <div class="record-label">

                Removed

              </div>


              <ul class="record-list">


                {% for path in latest_record.deleted %}

                  <li class="record-deleted">

                    {{ path }}

                  </li>

                {% endfor %}


              </ul>


            </div>


          {% endif %}



        </div>


      </details>



    {% endif %}


  {% endif %}






  {%- comment -%}
  =========================================================
  Previous versions

  구조:

  Previous versions
      날짜
          Record 내용 즉시 표시

          Files
              클릭했을 때만 파일 목록 표시
  =========================================================
  {%- endcomment -%}


  {% if dates.size > 1 %}



    <details class="previous-versions">



      <summary class="previous-summary">

        Previous versions

      </summary>



      <div class="previous-version-list">




        {% for date in dates %}



          {% unless date == latest_date %}




            <details class="version-folder">



              <summary class="version-summary">

                {{ date }}

              </summary>




              <div class="version-content">





                {%- comment -%}
                =================================================
                해당 날짜 Record

                날짜를 여는 순간 바로 보인다.
                Record 자체를 details로 감싸지 않는다.
                =================================================
                {%- endcomment -%}


                {% assign version_record = site.data.untexed_records[date] %}



                {% if version_record %}



                  {% assign has_added = version_record.added.size %}
                  {% assign has_modified = version_record.modified.size %}
                  {% assign has_moved = version_record.moved_renamed.size %}
                  {% assign has_deleted = version_record.deleted.size %}




                  {% if has_added > 0 or has_modified > 0 or has_moved > 0 or has_deleted > 0 %}




                    <div class="record-static">



                      <div class="record-heading">

                        Record

                      </div>




                      <div class="record-content">




                        {%- comment -%}
                        Added
                        {%- endcomment -%}


                        {% if version_record.added.size > 0 %}



                          <div class="record-section">



                            <div class="record-label">

                              Added

                            </div>



                            <ul class="record-list">



                              {% for path in version_record.added %}


                                <li class="record-added">

                                  {{ path }}

                                </li>


                              {% endfor %}



                            </ul>



                          </div>



                        {% endif %}






                        {%- comment -%}
                        Modified
                        {%- endcomment -%}


                        {% if version_record.modified.size > 0 %}



                          <div class="record-section">



                            <div class="record-label">

                              Modified

                            </div>



                            <ul class="record-list">



                              {% for path in version_record.modified %}


                                <li class="record-modified">

                                  {{ path }}

                                </li>


                              {% endfor %}



                            </ul>



                          </div>



                        {% endif %}






                        {%- comment -%}
                        Moved / Renamed
                        {%- endcomment -%}


                        {% if version_record.moved_renamed.size > 0 %}



                          <div class="record-section">



                            <div class="record-label">

                              Moved / Renamed

                            </div>



                            <ul class="record-list">



                              {% for move in version_record.moved_renamed %}



                                <li class="record-moved">



                                  <span class="record-move-from">

                                    {{ move.from }}

                                  </span>



                                  <span class="record-arrow">

                                    →

                                  </span>



                                  <span class="record-move-to">

                                    {{ move.to }}

                                  </span>



                                </li>



                              {% endfor %}



                            </ul>



                          </div>



                        {% endif %}






                        {%- comment -%}
                        Removed
                        {%- endcomment -%}


                        {% if version_record.deleted.size > 0 %}



                          <div class="record-section">



                            <div class="record-label">

                              Removed

                            </div>



                            <ul class="record-list">



                              {% for path in version_record.deleted %}


                                <li class="record-deleted">

                                  {{ path }}

                                </li>


                              {% endfor %}



                            </ul>



                          </div>



                        {% endif %}




                      </div>



                    </div>




                  {% endif %}



                {% endif %}







                {%- comment -%}
                =================================================
                해당 날짜 전체 파일 목록

                기본적으로 숨겨진다.

                Files를 클릭해야만 표시된다.
                =================================================
                {%- endcomment -%}



                <details class="version-files-toggle">



                  <summary class="files-summary">

                    Files

                  </summary>




                  <div class="version-files">



                    {% assign last_folder_str = "" %}
                    {% assign last_subject = "" %}
                    {% assign first_folder = true %}




                    {% for file in pdf_files %}




                      {% if file.extname == ".pdf" or file.extname == ".PDF" %}




                        {% assign current_path_parts = file.path | split: "/" %}
                        {% assign file_date = current_path_parts[2] %}




                        {% if file_date == date %}





                          {%- comment -%}
                          Subject 판정
                          {%- endcomment -%}


                          {% if current_path_parts.size > 4 %}

                            {% assign current_subject = current_path_parts[3] %}

                          {% else %}

                            {% assign current_subject = "General" %}

                          {% endif %}






                          {%- comment -%}
                          실제 폴더 경로
                          {%- endcomment -%}


                          {% assign folder_parts = "" | split: "" %}



                          {% for part in current_path_parts %}


                            {% if forloop.index > 3 and forloop.last == false %}

                              {% assign folder_parts = folder_parts | push: part %}

                            {% endif %}


                          {% endfor %}




                          {% capture current_folder_str %}

                            {{ folder_parts | join: " / " }}

                          {% endcapture %}


                          {% assign current_folder_str = current_folder_str | strip %}




                          {% if current_folder_str == "" %}

                            {% assign current_folder_str = "General" %}

                          {% endif %}







                          {%- comment -%}
                          새로운 폴더 시작
                          {%- endcomment -%}


                          {% if current_folder_str != last_folder_str %}





                            {% if first_folder == false %}

                              </ul>
                              </details>

                            {% endif %}






                            {%- comment -%}
                            Subject 변경
                            {%- endcomment -%}


                            {% if current_subject != last_subject %}



                              <div class="subject-divider nested-subject-divider">


                                <div class="subject-title">

                                  {{ current_subject | replace: "_", " " }}

                                </div>


                              </div>



                              {% assign last_subject = current_subject %}



                            {% endif %}






                            <details class="academic-folder nested-folder">



                              <summary class="folder-summary">


                                <span class="folder-label">

                                  {{ current_folder_str | replace: "_", " " }}

                                </span>


                              </summary>



                              <ul class="file-list">




                            {% assign last_folder_str = current_folder_str %}
                            {% assign first_folder = false %}



                          {% endif %}






                          <li class="file-item">



                            <a
                              href="{{ file.path | relative_url }}"
                              target="_blank"
                              class="file-link"
                            >

                              {{ file.basename }}

                            </a>



                          </li>





                        {% endif %}




                      {% endif %}




                    {% endfor %}





                    {%- comment -%}
                    마지막 폴더 닫기
                    {%- endcomment -%}


                    {% if first_folder == false %}

                      </ul>
                      </details>

                    {% endif %}




                  </div>



                </details>





              </div>




            </details>




          {% endunless %}



        {% endfor %}




      </div>



    </details>



  {% endif %}



</div>






<style>


  /* =====================================================
     전체 컨테이너
     ===================================================== */


  .academic-tree-container {

    font-family: "Times New Roman", Times, serif;

    line-height: 1.6;

    max-width: 100%;

    margin: 2rem 0;

    color: #1a1a1a;

  }





  /* =====================================================
     Subject 구분

     ALGEBRA
     --------------------------------

     ANALYSIS
     --------------------------------

     TOPOLOGY
     --------------------------------
     ===================================================== */


  .subject-divider {

    margin-top: 2.8rem;

    margin-bottom: 0.8rem;

    padding-bottom: 0.5rem;

    border-bottom: 1px solid #ddd;

  }



  .subject-divider:first-child {

    margin-top: 0;

  }



  .subject-title {

    font-size: 0.9rem;

    font-weight: 600;

    letter-spacing: 0.08em;

    text-transform: uppercase;

    color: #777;

  }





  /* =====================================================
     Previous version 내부 Subject
     ===================================================== */


  .nested-subject-divider {

    margin-top: 2rem;

    margin-bottom: 0.6rem;

  }



  .version-files > .nested-subject-divider:first-child {

    margin-top: 1rem;

  }





  /* =====================================================
     학술 폴더
     ===================================================== */


  .academic-folder {

    margin-bottom: 0.5rem;

    border-bottom: 1px solid #eee;

  }



  .folder-summary {

    list-style: none !important;

    padding: 0.75rem 0;

    cursor: pointer;

    font-weight: 600;

    font-size: 1.1rem;

    display: flex;

    align-items: center;

    color: #2c3e50;

  }



  .folder-summary::-webkit-details-marker {

    display: none;

  }



  .folder-summary::before {

    content: "\2020";

    margin-right: 12px;

    color: #999;

    font-weight: normal;

    font-family: serif;

  }



  .academic-folder[open] > .folder-summary::before {

    content: "\2021";

    color: #000;

  }





  /* =====================================================
     PDF 파일 목록
     ===================================================== */


  .academic-tree-container .file-list {

    list-style: none !important;

    padding: 0 0 1rem 1.5rem !important;

    margin: 0 !important;

  }



  .academic-tree-container .file-item {

    margin: 0.4rem 0 !important;

    padding-left: 1.2rem !important;

    position: relative !important;

    list-style: none !important;

  }



  .academic-tree-container .file-item::before {

    content: "\2013" !important;

    position: absolute !important;

    left: 0 !important;

    color: #999 !important;

    font-weight: normal !important;

  }



  .file-link {

    text-decoration: none !important;

    color: #555 !important;

    font-size: 0.95rem !important;

    transition: all 0.2s;

  }



  .file-link:hover {

    color: #000 !important;

    text-decoration: underline !important;

    text-underline-offset: 3px;

  }





  /* =====================================================
     Record 공통
     ===================================================== */


  .record-content {

    padding: 0.8rem 0 0.5rem 1.3rem;

  }



  .record-section {

    margin-bottom: 0.9rem;

  }



  .record-label {

    font-size: 0.85rem;

    font-weight: 600;

    color: #777;

    margin-bottom: 0.25rem;

  }



  .record-list {

    list-style: none !important;

    margin: 0 !important;

    padding: 0 0 0 1rem !important;

  }



  .record-list li {

    position: relative;

    list-style: none !important;

    margin: 0.25rem 0;

    padding-left: 1.3rem;

    font-size: 0.85rem;

    color: #777;

    overflow-wrap: anywhere;

  }





  /* =====================================================
     Added
     ===================================================== */


  .record-added::before {

    content: "+";

    position: absolute;

    left: 0;

  }





  /* =====================================================
     Modified
     ===================================================== */


  .record-modified::before {

    content: "~";

    position: absolute;

    left: 0;

  }





  /* =====================================================
     Removed
     ===================================================== */


  .record-deleted::before {

    content: "\2212";

    position: absolute;

    left: 0;

  }





  /* =====================================================
     Moved / Renamed
     ===================================================== */


  .record-moved::before {

    content: "\2192";

    position: absolute;

    left: 0;

  }



  .record-arrow {

    display: inline-block;

    margin: 0 0.45rem;

    color: #aaa;

  }



  .record-move-from {

    color: #888;

  }



  .record-move-to {

    color: #666;

  }





  /* =====================================================
     최신 버전 Record

     기본적으로 접혀 있음
     ===================================================== */


  .change-record {

    margin: 1rem 0 1.5rem 0;

  }



  .latest-record {

    margin-top: 2rem;

  }



  .record-summary {

    list-style: none !important;

    cursor: pointer;

    font-size: 0.9rem;

    color: #888;

    font-weight: 600;

  }



  .record-summary::-webkit-details-marker {

    display: none;

  }



  .record-summary::before {

    content: "\25B8";

    display: inline-block;

    margin-right: 8px;

    transition: transform 0.15s;

  }



  .change-record[open] > .record-summary::before {

    transform: rotate(90deg);

  }





  /* =====================================================
     Previous versions
     ===================================================== */


  .previous-versions {

    margin-top: 2rem;

    padding-top: 1rem;

    border-top: 1px solid #ddd;

  }



  .previous-summary {

    list-style: none !important;

    cursor: pointer;

    font-size: 0.95rem;

    color: #777;

    font-weight: 600;

  }



  .previous-summary::-webkit-details-marker {

    display: none;

  }



  .previous-summary::before {

    content: "\25B8";

    display: inline-block;

    margin-right: 8px;

    transition: transform 0.15s;

  }



  .previous-versions[open] > .previous-summary::before {

    transform: rotate(90deg);

  }



  .previous-version-list {

    margin-top: 0.8rem;

    padding-left: 1rem;

  }





  /* =====================================================
     Previous version 날짜
     ===================================================== */


  .version-folder {

    margin: 0.45rem 0;

  }



  .version-summary {

    list-style: none !important;

    cursor: pointer;

    color: #777;

    font-size: 0.95rem;

  }



  .version-summary::-webkit-details-marker {

    display: none;

  }



  .version-summary::before {

    content: "\25B8";

    display: inline-block;

    margin-right: 8px;

    transition: transform 0.15s;

  }



  .version-folder[open] > .version-summary::before {

    transform: rotate(90deg);

  }



  .version-content {

    padding-left: 1.2rem;

    margin-top: 0.6rem;

  }





  /* =====================================================
     Previous version Record

     날짜를 열면 즉시 보인다.
     ===================================================== */


  .record-static {

    margin-top: 0.8rem;

    margin-bottom: 1.4rem;

  }



  .record-heading {

    font-size: 0.95rem;

    font-weight: 600;

    color: #666;

    margin-bottom: 0.35rem;

  }



  .record-static .record-content {

    padding: 0.4rem 0 0.5rem 1.2rem;

  }





  /* =====================================================
     Previous version Files

     기본적으로 닫힘.
     클릭해야 표시.
     ===================================================== */


  .version-files-toggle {

    margin-top: 1.2rem;

    padding-top: 0.9rem;

    border-top: 1px solid #eee;

  }



  .files-summary {

    list-style: none !important;

    cursor: pointer;

    font-size: 0.9rem;

    font-weight: 600;

    color: #777;

  }



  .files-summary::-webkit-details-marker {

    display: none;

  }



  .files-summary::before {

    content: "\25B8";

    display: inline-block;

    margin-right: 8px;

    transition: transform 0.15s;

  }



  .version-files-toggle[open] > .files-summary::before {

    transform: rotate(90deg);

  }



  .version-files {

    margin-top: 0.8rem;

  }





  /* =====================================================
     Previous version 내부 폴더
     ===================================================== */


  .nested-folder .folder-summary {

    font-size: 0.95rem;

    padding: 0.4rem 0;

  }





  /* =====================================================
     모바일
     ===================================================== */


  @media (max-width: 600px) {



    .subject-divider {

      margin-top: 2.2rem;

    }



    .subject-title {

      font-size: 0.82rem;

    }



    .folder-summary {

      font-size: 1rem;

    }



    .file-link {

      font-size: 0.9rem !important;

    }



    .previous-version-list {

      padding-left: 0.5rem;

    }



    .version-content {

      padding-left: 0.7rem;

    }



    .record-content {

      padding-left: 0.8rem;

    }



    .record-static .record-content {

      padding-left: 0.7rem;

    }



    .record-arrow {

      margin: 0 0.25rem;

    }



  }


</style>
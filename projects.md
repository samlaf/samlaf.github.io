---
layout: page
title: Projects
permalink: /projects/
---


<!-- Start of the section project-loop-->
<section class="project-loop container-fluid">
    {% for project in site.projects %}
    <div class="row single-project">
        <div>
            <h1 class="project-title"><a href="{{ project.url | prepend: site.baseurl }}">{{ project.title }}</a></h1>

            <div class="project-details">
                <span>{{ project.date | date: "%b %-d, %Y" }}</span>

            </div>

            <p class="project-excerpt">
                {{project.excerpt | length: 140 }}
            </p>

            <a class="project-button pi-big pi-retro pi-flat" href="{{ project.url }}">More</a>

        </div>
    </div>

    {% endfor %}
</section>




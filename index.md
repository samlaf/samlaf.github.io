---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults
---

<link rel="stylesheet" href="/assets/css/styles.css">

<!-- Blog Posts -->
<div id="home" style="height:100%; width:100%; overflow: hidden;">
	<div style="width:60%; float: left;">
	    {%- if page.title -%}
		<h1 class="page-heading">{{ page.title }}</h1>
		{%- endif -%}
		<h2> <a style="color:#000000" href="blog"> Blog Posts </a> </h2>
		<ul>
		{% for post in site.posts %}
			<li><a href="{{ post.url }}">{{ post.title }}</a></li>
		{% endfor %}
		</ul>
	</div>
	<div style="width:40%; float: left;">
		<img src="/assets/videos/duckiebots-driving-husky.gif"/>
	</div>
</div>

<!-- Projects -->
<div class='iconandproject'> 
	<h2> <a style="color:#000000" href="projects"> Projects </a> </h2>
	{% assign filtered_projects = site.projects | reverse %}
	{% for project in filtered_projects %}
		<div style="clear: left;">
		<img src="/assets/icons/{{project.slug}}.png" class='iconDetails'>
		</div>	
		<div style='margin-left:150px;'>
			<h4> <a href="{{ project.url }}">{{ project.title }}</a> </h4>
			<div style="font-size:.6em;"> {{ project.abstract | markdownify}} </div>
		</div>
	{% endfor %}
</div>

<center>
	<img src="/assets/images/sam-duckietown-montage.png" title="My montage" width="60%"/>
</center>
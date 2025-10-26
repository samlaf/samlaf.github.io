---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults
---

<!-- "Programming Articles" -->
<h2> <a style="color:#000000" href="blog"> Programming </a> </h2>
<ul>
{% for post in site.posts %}
	{% if post.category == "programming" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a></li>
	{% endif %}
{% endfor %}
</ul>

<!-- "Blockchain Articles" -->
<h2> <a style="color:#000000" href="blog"> Blockchain </a> </h2>
<ul>
{% assign blockchain_posts = site.posts | where: "category", "blockchain" %}
<!-- external articles are listed under _data/external_posts -->
{% assign all_posts = blockchain_posts | concat: site.data.external_posts.blockchain | sort: "date" | reverse %}
{% for post in all_posts %}
	<li><a href="{{ post.url }}">{{ post.title }}</a></li>
{% endfor %}
</ul>

<!-- "Other Blog Posts"  -->
<h2> <a style="color:#000000" href="blog"> Miscellaneous </a> </h2>
<ul>
{% for post in site.posts %}
	{% if post.category != "blockchain" and post.category != "programming" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a></li>
	{% endif %}
{% endfor %}
</ul>

<!-- Projects -->
<div class='iconandproject'> 
	<h2> <a style="color:#000000" href="projects"> Past Projects </a> </h2>
	{% assign filtered_projects = site.projects | reverse %}
	{% for project in filtered_projects %}
		<div style="clear: left;">
			<img src="/assets/icons/{{ project.slug }}.png" class='iconDetails'>
		</div>	
		<div style='margin-left:150px;'>
			<h4> <a href="{{ project.url }}">{{ project.title }}</a> </h4>
			<div style="font-size:.6em;"> {{ project.abstract | markdownify}} </div>
		</div>
	{% endfor %}
</div>

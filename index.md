---
# Feel free to add content and custom Front Matter to this file.
# To modify the layout, see https://jekyllrb.com/docs/themes/#overriding-theme-defaults
---

<!-- Blog Posts -->
<!-- "Blockchain Articles" -->
<h2> <a style="color:#000000" href="blog"> Blockchain Articles </a> </h2>
<ul>
		<!-- Adding this by hand here for now. Might want to add in posts eventually to have date ordering -->
		<li><a href="https://hackmd.io/@samlaf/understanding-optimism-via-confusion-resolution-devnet-explorations">Optimism via Confusion-Resolution Devnet Explorations</a></li>
		<li><a href="https://hackmd.io/@samlaf/based-preconfs-faq">Based Preconfs FAQ</a></li>
		<li><a href="https://hackmd.io/@0xtrojan/mev_meets_dag">MEV meets DAG: Exploring MEV in DAG-based blockchains</a></li>
		<li><a href="https://www.notion.so/samlaf/Themis-For-The-Rest-Of-Us-1d543162f87445528ee3d850c2f57d0f">Themis for the Rest of Us</a></li>
{% for post in site.posts %}
	{% if post.category == "blockchain" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a></li>
	{% endif %}
{% endfor %}
</ul>

<!-- "Other Blog Posts"  -->
<h2> <a style="color:#000000" href="blog"> Other Blog Posts </a> </h2>
<ul>
{% for post in site.posts %}
	{% if post.category != "blockchain" %}
		<li><a href="{{ post.url }}">{{ post.title }}</a></li>
	{% endif %}
{% endfor %}
</ul>

<!-- <div style="width:40%; float: left;">
	<img src="/assets/videos/duckiebots-driving-husky.gif"/>
</div> -->

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


html_file = 'obama_addresses.html'
with open(html_file, 'r') as f:
	text = f.read()

search_text = 'watch?v='
video_ids = []

pos = 0
i = 0
while i != -1:
	i = text.find(search_text, pos)
	quote_stop = text.find('"', i+1)
	and_stop = text.find('&', i+1)
	if and_stop != -1:
		stop_pos = min(quote_stop, and_stop)
	else:
		stop_pos = quote_stop
	video_ids.append(text[i+len(search_text):stop_pos])
	pos = i+1

video_ids = ['https://www.youtube.com/watch?v=%s' % video_id for video_id in list(set(video_ids))]
text = '\n'.join(video_ids)

with open('obama_addresses_html.txt', 'w') as f:
	f.write(text)

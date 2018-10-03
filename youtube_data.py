import subprocess
import sys
import os
import glob
import nlpre
import inflect
import numpy as np

def download(url):
	cmd = 'youtube-dl -q -x --restrict-filenames --audio-format wav --audio-quality 0 --write-sub --write-auto-sub --sub-format vtt --id %s' % url
	cmd = cmd.split(' ')
	p = subprocess.Popen(cmd)
	p.wait()

def vtt2srt(file):
	out_file = file.split('.en.vtt')[0] + '.srt'
	cmd = 'ffmpeg -y -loglevel error -i %s %s' % (file, out_file)
	cmd = cmd.split(' ')
	p = subprocess.Popen(cmd)
	p.wait()
	return out_file

def parse_srt(seg_dict, file, min_duration):
	seg_dict[file] = {}
	speakers = []
	with open(file, 'r') as f:
		lines = f.readlines()
	lines = [line.replace('\n', '') for line in lines]
	# print(lines)
	count = 1
	line_hold = 0
	while True:
		if not str(count) in lines:
			break
		index = lines.index(str(count))
		seg_dict[file][count] = {}
		seg_dict[file][count]['slice'] = lines[index + 1]
		# print(seg_dict[file][count]['slice'])
		from_time = seg_dict[file][count]['slice'].split(' --> ')[0]
		to_time = seg_dict[file][count]['slice'].split(' --> ')[1]
		# print(from_time)
		# print(to_time)
		from_sec = float('0.' + from_time.split(',')[-1])
		for i, num in enumerate(reversed(from_time.split(',')[0].split(':'))):
			from_sec += (60**i)*int(num)
		to_sec = float('0.' + to_time.split(',')[-1])
		for i, num in enumerate(reversed(to_time.split(',')[0].split(':'))):
			to_sec += (60**i)*int(num)
		seg_dict[file][count]['slice'] = (from_sec, to_sec)
		if str(count + 1) in lines:
			next_index = lines.index(str(count + 1))
		else:
			next_index = len(lines) - 1
		seg_dict[file][count]['text'] = [line.split(':')[-1] for line in lines[index + 2:next_index]]
		speakers += [line.split(':')[0] for line in lines[index + 2:next_index] if line.find(':') != -1]
		while '' in seg_dict[file][count]['text']:
			seg_dict[file][count]['text'].remove('')
		seg_dict[file][count]['text'] = ' '.join(seg_dict[file][count]['text'])
		if seg_dict[file][count]['text'].replace(' ', '') == '' or (to_sec - from_sec) < min_duration:
			del seg_dict[file][count]
		count += 1
	speakers = [speaker for speaker in speakers if speaker.strip() != '']
	if len(list(set(speakers))) > 1:
		max_occ = 3
		actual_speakers = []
		for speaker in list(set(speakers)):
			occ = speakers.count(speaker)
			if occ > max_occ:
				actual_speakers.append(speaker)
		if len(actual_speakers) > 1:
			print('Multiple Speakers Detected, skipping: %s' % file)
			del(seg_dict[file])
	return seg_dict

def text_overlap(text1, text2):
	text1 = text1.strip().split(' ')
	text2 = text2.strip().split(' ')
	combined_text = ''
	max_overlap = min(len(text1), len(text2))
	for overlap in reversed(range(1,max_overlap+1)):
		if text1[overlap*-1:] == text2[:overlap+1]:
			combined_text = text1[:overlap*-1] + text2
			combined_text = ' '.join(combined_text)
			break
	if combined_text == '':
		combined_text = text1 + text2
		combined_text = ' '.join(combined_text)
	return combined_text

def merge_segments(seg_dict, target_duration, max_duration):
	target_seg_dict = {}
	for file in seg_dict:
		target_seg_dict[file] = {}
		snippets = list(seg_dict[file].keys())
		count = 1
		target_seg_dict[file][0] = seg_dict[file][snippets[0]]
		while count < len(snippets):
			snippet = list(target_seg_dict[file].keys())[-1]
			from_sec = target_seg_dict[file][snippet]['slice'][0]
			to_sec = target_seg_dict[file][snippet]['slice'][1]
			duration = to_sec - from_sec
		# for i, snippet in enumerate(snippets):
		# 	if i < count:
		# 		continue
		# 	duration = seg_dict[file][snippet]['slice'][1] - seg_dict[file][snippet]['slice'][0]
		# 	from_sec = seg_dict[file][snippet]['slice'][0]
		# 	to_sec = seg_dict[file][snippet]['slice'][1]
			if duration < target_duration:
				next_from_sec = seg_dict[file][snippets[count]]['slice'][0]
				next_to_sec = seg_dict[file][snippets[count]]['slice'][1]
				combined_duration = next_to_sec - from_sec
				if combined_duration < max_duration:
					combined_text = text_overlap(target_seg_dict[file][snippet]['text'], seg_dict[file][snippets[count]]['text'])
					# if combined_text:
					target_seg_dict[file][snippet] = {
					'slice': (from_sec, next_to_sec),
					'text': combined_text
					}
					count += 1
					# else:
					# 	target_seg_dict[file][len(target_seg_dict[file].keys())] = seg_dict[file][snippet]
					# 	count += 1
				# elif combined_duration < max_duration:
				# 	combined_text = text_overlap(seg_dict[file][snippet]['text'], seg_dict[file][snippets[i+1]]['text'])
				# 	# if combined_text:
				# 	target_seg_dict[file][len(target_seg_dict[file].keys())] = {
				# 	'slice': (from_sec, next_to_sec),
				# 	'text': combined_text
				# 	}
				# 	count += 2
				# elif next_to_sec - next_from_sec < max_duration:
				# 	target_seg_dict[file][len(target_seg_dict[file].keys())] = seg_dict[file][snippets[count]]
				# 	count += 1
				else:
					while seg_dict[file][snippets[count]]['slice'][1] - seg_dict[file][snippets[count]]['slice'][0] >= max_duration and count < len(snippets):
						count += 1
					target_seg_dict[file][len(target_seg_dict[file].keys())] = seg_dict[file][snippets[count]]
					count +=1
			# elif duration < max_duration:
			# 	target_seg_dict[file][len(target_seg_dict[file].keys())] = seg_dict[file][snippets[count]]
			# 	count += 1
			else:
				while seg_dict[file][snippets[count]]['slice'][1] - seg_dict[file][snippets[count]]['slice'][0] >= max_duration and count < len(snippets):
					count += 1
				target_seg_dict[file][len(target_seg_dict[file].keys())] = seg_dict[file][snippets[count]]
				count += 1
	return target_seg_dict

def clean_text(text):
	no_digits = []
	for s in text.split(' '):
		if s.isdigit():
			p = inflect.engine()
			no_digits.append(p.number_to_words(s))
		else:
			no_digits.append(s)
	text = ' '.join(no_digits)
	for f in [nlpre.token_replacement(), nlpre.dedash(), nlpre.separated_parenthesis(), nlpre.replace_acronyms(nlpre.identify_parenthetical_phrases()(text))]: #, nlpre.decaps_text(), nlpre.titlecaps()
		text = f(text)
	if text[-1] == '.' and no_digits[-1][-1] != '.':
		text = text[:-1]
	text = text.replace('\n', ' ')
	return text

def create_files(seg_dict, file_hz):
	metadata = []
	for srt_file in seg_dict:
		wav_file = srt_file.split('.srt')[0] + '.wav'
		count = 0
		for snippet in seg_dict[srt_file]:
			text = seg_dict[srt_file][snippet]['text']
			clean = clean_text(text)
			if clean.strip() == '':
				continue
			snippet_file = srt_file.split('.srt')[0] + '_%s' % count
			cmd = 'ffmpeg -y -loglevel error -i %s -acodec copy -ar %s -ss %s -to %s %s' % (os.path.join('raw', wav_file), file_hz, seg_dict[srt_file][snippet]['slice'][0], seg_dict[srt_file][snippet]['slice'][1], os.path.join('wavs', '%s.wav' % snippet_file))
			cmd = cmd.split(' ')
			p = subprocess.Popen(cmd)
			p.wait()
			metadata.append('%s|%s|%s\n' % (snippet_file, text, clean))
			count += 1
	with open('metadata.csv', 'w') as f:
		f.writelines(metadata)

def summarize(seg_dict):
	durations = []
	words = []
	for file in seg_dict:
		for snippet in seg_dict[file]:
			durations.append(seg_dict[file][snippet]['slice'][1] - seg_dict[file][snippet]['slice'][0])
			words.append(len(seg_dict[file][snippet]['text'].strip().split(' ')))

	duration = np.sum(durations)
	mean_duration = np.mean(durations)
	max_duration = np.max(durations)
	min_duration = np.min(durations)
	num_snippets = len(durations)
	mean_word_count = np.mean(words)

	summary = '\n*****Summary*****'
	summary += '\nTotal audio duration: %s minutes' % round(duration/60., 1)
	summary += '\nNumber of audio snippets: %s' % num_snippets
	summary += '\nAverage snippet duration: %s seconds' % mean_duration
	summary += '\nMax snippet duration: %s seconds' % max_duration
	summary += '\nMin snippet duration: %s seconds' % min_duration
	summary += '\nAverage snippet word count: %s' % mean_word_count
	summary += '\n*****************'
	return summary

if __name__ == '__main__':
	urls_file = sys.argv[1]
	file_hz = sys.argv[2]
	min_duration = float(sys.argv[3])
	target_duration = float(sys.argv[4])
	max_duration = float(sys.argv[5])
	outdir = sys.argv[6]
	start_pad = float(sys.argv[7])
	end_pad = float(sys.argv[8])

	with open(urls_file, 'r') as f:
		urls = f.readlines()

	if not os.path.exists(outdir):
		os.makedirs(outdir)
	os.chdir(outdir)
	if not os.path.exists('raw'):
		os.mkdir('raw')
	if not os.path.exists('wavs'):
		os.mkdir('wavs')

	os.chdir('raw')

	print('Downloading data...')
	for url in urls:
		download(url)

	for file in glob.glob('.wav'):
		if len(glob.glob(file.split('.wav')[0] + '*.vtt')) == 0:
			os.remove(file)
	for file in glob.glob('*-*'):
		os.rename(file, file.replace('-', ''))

	seg_dict = {}
	print('\nParsing text segmentations...')
	for vtt_file in glob.glob('*.vtt'):
		srt_file = vtt2srt(vtt_file)
		seg_dict = parse_srt(seg_dict, srt_file, min_duration)
	os.chdir('..')

	print('\nCombining overlapping segments...')
	seg_dict = merge_segments(seg_dict, target_duration, max_duration)

	print('\nProcessing audio...')
	create_files(seg_dict, file_hz)

	summary = summarize(seg_dict)
	print(summary)



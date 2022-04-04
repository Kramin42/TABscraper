from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from time import sleep
import datetime as dt
import yaml
import pathlib
from collections import namedtuple

SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()

Game = namedtuple("Game", [
	'date',
	'home_team_name',
	'away_team_name',
	'home_team_payout',
	'away_team_payout'])

def games_to_csv(games, header=False):
	lines = []
	if header:
		lines.append(','.join(Game._fields))
	for g in games:
		lines.append(','.join([str(x) for x in g]))
	return '\n'.join(lines)+'\n'

CONFIG_FILE = SCRIPT_DIR / 'config.yaml'
if not pathlib.Path(CONFIG_FILE).is_file():
	print("WARNING: config.yaml not found, using default-config.yaml")
	CONFIG_FILE = SCRIPT_DIR / 'default-config.yaml'

with open(CONFIG_FILE, 'r') as f:
	CONFIG = yaml.load(f)

print(CONFIG)

pathlib.Path(CONFIG['tomorrow-games-path']).parent.mkdir(parents=True, exist_ok=True)
pathlib.Path(CONFIG['all-games-path']).parent.mkdir(parents=True, exist_ok=True)

tomorrow_datetime = dt.date.today() + dt.timedelta(days=1)
games = []

opts = Options()
opts.set_headless()
browser = Chrome(options=opts)
try:
	browser.get(CONFIG['matches-url'])

	sleep(CONFIG['loading-time']) # TODO: find a way to wait until page finishes loading

	load_more_links = browser.find_elements_by_class_name('content-loader__load-more-link')
	for link in load_more_links:
		# load_more_link.click()
		# call js click method instead, works in headless
		browser.execute_script("arguments[0].click();", link)

	sleep(CONFIG['loading-time'])

	#today_heading = browser.find_element_by_class_name('heading--timeband--today')
	success = True
	try:
		tomorrow_heading = browser.find_element_by_class_name('heading--timeband--tomorrow')

		#for heading in [today_heading, tomorrow_heading]:
		event_list = tomorrow_heading.find_element_by_class_name('event-list__content')
		for item in event_list.find_elements_by_tag_name("li"):
			mbcs = item.find_elements_by_class_name('market__body_col')
			if len(mbcs)==0:
				continue
			try:
				el_title_A = mbcs[0].find_element_by_class_name('button--outcome__text')
				el_price_A = mbcs[0].find_element_by_class_name('button--outcome__price')
				el_title_B = mbcs[1].find_element_by_class_name('button--outcome__text')
				el_price_B = mbcs[1].find_element_by_class_name('button--outcome__price')
				el_time = item.find_element_by_class_name('event-card__event-time__date-time')
			except NoSuchElementException as e:
				print(e)
				continue
			str_time = el_time.text
			if not str_time.startswith('Tomorrow '):
				print(f'invalid time string: {str_time}')
				continue
			game_time = dt.datetime.strptime(str_time.replace('Tomorrow ', ''), '%H.%M%p').time()
			game_dt = dt.datetime.combine(tomorrow_datetime, game_time)
			games.append(Game(
				date=game_dt.isoformat(),
				home_team_name=el_title_A.text,
				away_team_name=el_title_B.text,
				home_team_payout=el_price_A.text,
				away_team_payout=el_price_B.text))
			print(f'{el_title_A.text} ({el_price_A.text}) vs {el_title_B.text} ({el_price_B.text}) on {game_dt.strftime("%d/%m/%Y")}')
	except Exception as e:
		success = False
		print(e)

	print(games)
	with open(CONFIG['tomorrow-games-path'], 'w') as f:
		f.write(games_to_csv(games, header=True))

	if success:
		write_header = not pathlib.Path(CONFIG['all-games-path']).is_file()
		with open(CONFIG['all-games-path'], 'a') as f:
			f.write(games_to_csv(games, write_header))
finally:
	#input('press enter to finish')
	browser.quit()

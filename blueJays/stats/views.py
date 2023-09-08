import requests
from xml.etree import ElementTree
from django.shortcuts import render

url = 'https://statsapi.mlb.com'
url_log = 'https://www.mlbstatic.com/team-logos'
url_news = 'https://www.mlb.com/feeds/news/rss.xml'
url_divisions = f'{url}/api/v1/standings?leagueId=103,104'
url_head_shot = 'https://content.mlb.com/images/headshots/current/60x60/'
url_team = f'{url}/api/v1/teams/'
url_player = f'{url}/api/v1/people/'

def home(request):
    return render(request, 'index.html', {
        'divisions_data': divisions(), 
        'news_lst': news()
    })


def team(request, pk):
    player_type = "hitting"
    if request.GET.get('player_type') == 'pitching':
        player_type = 'pitching'

    team, roster = this_team(pk)

    return render(request, 'team.html', {
        'team_data': team,
        'roster_data': filter_roster(roster, player_type),
        'player_type': player_type
    })


def this_team(pk):
    team_data = requests.get(f'{url_team}{pk}')
    roster_data = requests.get(f'{url_team}{pk}/roster/Active?hydrate=person(stats(type=season))')

    team = team_data.json()['teams'][0]
    team['team_log_url'] = f"{url_log}/{team['id']}.svg"

    roster = roster_data.json()['roster']
    for player in roster:
        player['head_shot_url'] = f"{url_head_shot}{player['person']['id']}@2x.png"

    return (team, roster)


# separate hitters and pitchers
def filter_roster(roster, player_type):
    hitters = []
    pitchers = []
    for player in roster:
        if player['position']['code']=='1':
            pitchers.append(player)
        else:
            hitters.append(player)
    
    if player_type == 'pitching':
        return pitchers
    else:
        return hitters


def player(request, pk):
    player_type = "hitting"
    if request.GET.get('player_type') == 'pitching':
        player_type = 'pitching'

    player_data, records = this_player(pk, player_type)

    return render(request, 'player.html', {
        'player_data': player_data,
        'records': records
        })


def this_player(pk, player_type):
    player_data = requests.get(f'{url_player}{pk}?hydrate=stats(group=[{player_type}],type=[yearByYear])')
    player = player_data.json()['people'][0]
    player['head_shot_url'] = f"{url_head_shot}{player['id']}@3x.png"

    records = player['stats'][0]['splits']

    for record in records:
        record['team_log_url'] = f"{url_log}/{record['team']['id']}.svg"

    player['current_team_id'] = records[-1]['team']['id']
    player['current_team_name'] = records[-1]['team']['name']
    return player, records

# get news feeds data
def news():
    news_feeds = requests.get(url_news)
    tree = ElementTree.fromstring(news_feeds.content)

    news_lst = []

    # the current setting only show four news feeds
    i = 0
    for item in tree[0].findall('item'):
        if i>3: break
        news_dict = {
            'title': item.find('title').text,
            'link': item.find('link').text,
            'date': item.find('pubDate').text[0:16],
            'creator': item.find('{http://purl.org/dc/elements/1.1/}creator').text or '',
            'image_url': item.find('image').attrib['href'],
        }
        news_lst.append(news_dict)
        i+=1
    return news_lst


def divisions():
    data = requests.get(url_divisions)
    standings = data.json()["records"]
    standing_lst = []
    for standing in standings:
        standing_dict = {
            'division_abbr': division_name_helper(standing['division']['link']),
        }

        team_list = []
        for team in standing['teamRecords']:
            team_dict = {
                'team_id': team['team']['id'],
                'team_abbr': team['team']['name'],
                'team_log_url': f"{url_log}/{team['team']['id']}.svg",
                'leagueRecord': team['leagueRecord'],
                'gamesBack': team['gamesBack'],
                'records': team_record_helper(team['records']['splitRecords']),
            }
            team_list.append(team_dict)

        standing_dict['teams'] = team_list

        standing_lst.append(standing_dict)

    return data_process(standing_lst)


# change list with 6 items to list with 3 items
def data_process(lst):
    good = []
    for i in range(0, len(lst), 2):
        tup = (lst[i], lst[i+1])
        if i+1 >= len(lst):
            tup = (lst[i], {})
        good.append(tup)
    return good


# return division short name
def division_name_helper(link):
    data = requests.get(f'{url}{link}')
    division = (data.json()['divisions'])[0]
    return division['nameShort']


# return team short name
def team_name_helper(link):
    data = requests.get(f'{url}{link}')
    team = (data.json()['teams'])[0]
    return team['abbreviation']


# return last ten records
def team_record_helper(lst):
    my_dict = {}
    for item in lst:
        if item['type'] == 'lastTen':
            my_dict['lastTen'] = item
        if item['type'] == 'home':
            my_dict['home'] = item
        if item['type'] == 'away':
            my_dict['away'] = item
    return my_dict

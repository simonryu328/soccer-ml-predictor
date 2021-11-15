import os
from datetime import datetime
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath('__file__'))
DATA_DIR = os.path.join(BASE_DIR,'ml','data', 'raw')
DATA_FEATURED_DIR = os.path.join(BASE_DIR, 'ml', 'data', 'featured')

df = pd.read_csv(os.path.join(DATA_DIR, 'epl_matches.csv'))

df['season'] = df.season.str.split('/').str[0]
df['date'] = df['date'].apply(datetime.strptime, args=('%d %b %Y', ))
df[['h_team', 'a_team']] = df['match_name'].str.split(' - ', expand=True)
df[['h_score', 'a_score']] = df['result'].str.split(':', expand=True)
df['winner'] = np.where(df.h_score > df.a_score, 'h', np.where(df.a_score > df.h_score, 'a', 'd'))
#home points made in each match
df['h_match_points'] = np.where(df['winner'] == 'h', 3 , np.where(df['winner'] == 'd',1, 0))
#away points made in each match
df['a_match_points'] = np.where(df['winner'] == 'a', 3 , np.where(df['winner'] == 'd',1, 0))

to_int = ['season', 'h_score', 'a_score']
to_float = ['h_odd', 'd_odd', 'a_odd']

for col in to_int:
    df[col] = df[col].astype(int)

for col in to_float:
    df[col] = df[col].str.replace('-', '0')
    df[col] = df[col].astype(float)

cols_order = ['season', 'date', 'h_team', 'a_team', 'winner', 'h_score', 'a_score',
                'h_odd', 'd_odd', 'a_odd', 'h_match_points', 'a_match_points']
df = df[cols_order]

def create_season_stats(x):
    season_df = df[(df.season == x.season) & (df.date <= x.date)]
    h_df = season_df.groupby(['h_team', 'date']).sum()[['h_match_points', 'h_score', 'a_score']].reset_index()
    a_df = season_df.groupby(['a_team', 'date']).sum()[['a_match_points', 'a_score', 'h_score']].reset_index()
    h_df.columns = ['team', 'date','points', 'goals_for', 'goals_against']
    a_df.columns = ['team', 'date','points', 'goals_for', 'goals_against']
    
    full_df = pd.concat([h_df, a_df], ignore_index=True).sort_values(['date'])
    full_df.loc[full_df.date == x.date, ['points', 'goals_for', 'goals_against']] = 0
    h_full_df = full_df[full_df.team == x.h_team]
    a_full_df = full_df[full_df.team == x.a_team]
    
    h_full_df['ewm_points'] = h_full_df.points.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    a_full_df['ewm_points'] = a_full_df.points.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    h_full_df['ewm_goals_for'] = h_full_df.goals_for.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    a_full_df['ewm_goals_for'] = a_full_df.goals_for.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    h_full_df['ewm_goals_against'] = h_full_df.goals_against.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    a_full_df['ewm_goals_against'] = a_full_df.goals_against.ewm(span=3, adjust=False).mean().shift(1).fillna(0)
    
    h_ewm_points = float(h_full_df[h_full_df.date == x.date]['ewm_points'])
    a_ewm_points = float(a_full_df[a_full_df.date == x.date]['ewm_points'])
    h_ewm_goals_for = float(h_full_df[h_full_df.date == x.date]['ewm_goals_for'])
    a_ewm_goals_for = float(a_full_df[a_full_df.date == x.date]['ewm_goals_for'])
    h_ewm_goals_against = float(h_full_df[h_full_df.date == x.date]['ewm_goals_against'])
    a_ewm_goals_against = float(a_full_df[a_full_df.date == x.date]['ewm_goals_against'])
    ewm_points = [h_ewm_points, h_ewm_goals_for, h_ewm_goals_against, a_ewm_points, a_ewm_goals_for, a_ewm_goals_against]
    
    cum_df = full_df.groupby(['team']).sum()[['points', 'goals_for', 'goals_against']]
    cum_df['standing'] = cum_df['points'].rank(ascending=False)
    standings = [cum_df.loc[x.h_team].standing, cum_df.loc[x.a_team].standing]
    
    h_stat = [0,0,0]
    a_stat = [0,0,0]
    try:
        h_stat = cum_df.loc[x.h_team][['points', 'goals_for', 'goals_against']].values
    except:
        pass
    try:
        a_stat = cum_df.loc[x.a_team][['points', 'goals_for', 'goals_against']].values
    except:
        pass
    
    return np.concatenate((standings, h_stat, a_stat, ewm_points))
    
def create_vs_stats(x):
    # Get all games where two teams played against each other.
    vs_df = df[(df.date <= x.date) & 
              (((df.h_team == x.h_team) & (df.a_team == x.a_team)) | ((df.h_team == x.a_team) & (df.a_team == x.h_team)))][['date','h_team', 'a_team', 'h_score', 'a_score']]
    vs_df.loc[vs_df.date == x.date, ['h_score', 'a_score']] = 0
               
    # Swap home and away columns.
    vs_df.loc[vs_df.h_team == x.a_team, ['h_team', 'a_team', 'h_score', 'a_score']] = vs_df.loc[vs_df.h_team == x.a_team,['a_team','h_team', 'a_score', 'h_score']].values

    h_vs_winrate = vs_df[vs_df.h_score > vs_df.a_score].shape[0]/vs_df.shape[0]
    a_vs_winrate = vs_df[vs_df.a_score > vs_df.h_score].shape[0]/vs_df.shape[0]
               
    return [h_vs_winrate, a_vs_winrate]

season_cols = ['h_standing', 'a_standing', 'ht_pts','ht_goals_for','ht_goals_against','at_pts','at_goals_for','at_goals_against',
               'h_ewm_points', 'h_ewm_goals_for', 'h_ewm_goals_against', 'a_ewm_points', 'a_ewm_goals_for', 'a_ewm_goals_against']
vs_cols = ['h_vs_winrate', 'a_vs_winrate']

featured_df = df.copy()
featured_df[season_cols] = pd.DataFrame(
    featured_df.apply(lambda x: create_season_stats(x), axis=1).to_list(), index=featured_df.index)

featured_df[vs_cols] = pd.DataFrame(
    featured_df.apply(lambda x: create_vs_stats(x), axis=1).to_list(), index=featured_df.index)

featured_df.to_csv(os.path.join(DATA_FEATURED_DIR, 'epl_matches_featured.csv'), index=False)

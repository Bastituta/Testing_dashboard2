# -*- coding: utf-8 -*-
"""
Created on Sun Feb 11 16:11:21 2024

@author: info
"""

# streamlit run dashboard_vlog.py

import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static
#from datetime import datetime, timedelta
import sqlite3
import streamlit as st
#import spatialite  # deze werkt niet in de streamlit cloud

#sqlitepath = './vlog/'

# Function to get user input
def get_user_input():


    cols = st.sidebar.columns(3)
   
    bufferscale = cols[0].number_input('Buffergrootte', value = 5, min_value = 2, max_value=15)
    st.sidebar.title('Selecteren data')

    date_range = st.sidebar.date_input("Datumreeks", (pd.to_datetime('2023-12-01'), pd.to_datetime('2023-12-31')))
    if len(date_range) != 2:
        st.stop()
        if len(str(date_range[0]))>0: date_range = (date_range[0],date_range[0])
        if len(str(date_range[1]))>0: date_range = (date_range[1],date_range[1])
        
    
    #print(date_range)

    # Split day names into four groups
    groups = [['Ma', 'Vr'], ['Di', 'Za'], ['Wo', 'Zo'], ['Do']]
    
    # Create four columns in the sidebar
    cols = st.sidebar.columns(4)
    
    selected_days = []
                        
    for i, group in enumerate(groups):
        for day_index, day in enumerate(group):
            key = f"{day}_{day_index}"  # Unique key for each checkbox
            selected = cols[i].checkbox(day, value=True, key = key)
            if selected:
                selected_days.append(day)

    time_range = st.sidebar.slider('Dagperiode', 0,24, (7, 9), step=1, key ='1')


    st.sidebar.text("")
    st.sidebar.text("")

    # referentiesituatie
    date_range_R = st.sidebar.date_input("Datumreeks referentie", (pd.to_datetime('2023-12-05'), pd.to_datetime('2023-12-10')))
    if len(date_range_R) != 2:
        st.stop()
        if len(str(date_range_R[0]))>0: date_range_R = (date_range_R[0],date_range_R[0])
        if len(str(date_range_R[1]))>0: date_range_R = (date_range_R[1],date_range_R[1])

    # Split day names into four groups
    
    # Create four columns in the sidebar
    cols = st.sidebar.columns(4)
    
    selected_days_R = []
                        
    for i, group in enumerate(groups):
        for day_index, day in enumerate(group):
            key = f"{day}_{day_index}_R"  # Unique key for each checkbox
            selected2 = cols[i].checkbox(day, value=True, key = key)
            if selected2:
                selected_days_R.append(day)

    time_range_R = st.sidebar.slider('Dagperiode referentie:', 0,24, (7, 9), step=1, key = '1_R')

    st.markdown(
        """
        <style>
            /* Adjust row height for sliders */
            .stSlider>div>div {
                height: 10px;
            }
            /* Adjust row height for date input */
            .stDateInput>div>div {
                height: 20px;
            }
            /* Adjust row height for text input */
            .stNumberInput>div>div {
                height: 15px;
                widht: 30 px;
            }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    return date_range, time_range, selected_days, date_range_R, time_range_R, selected_days_R, bufferscale



# Function to get user input
def maken_selecties():
    
    datums, periode, dagsoorten, datumsR, periodeR, dagsoortenR, bufferscale = get_user_input()
    
    #con = sqlite3.connect(sqlitepath + "vlogdashboard.sqlite")
    con = sqlite3.connect("vlogdashboard.sqlite")
    vdata = pd.read_sql_query("SELECT * from vlogdata", con)
    vdata['timestamp'] = pd.to_datetime(vdata['timestamp'])
    vdata['datum'] = vdata['timestamp'].dt.date
    vdata['weekdag'] = vdata['timestamp'].dt.weekday
    vdata['uur'] = vdata['timestamp'].dt.hour
    vdata['uur'] = vdata['uur'].astype(int)
    
    datumsdict = {'df1': datums, 'df2': datumsR}
    periodesdict = {'df1': periode, 'df2': periodeR}
    dagendict = {'df1': dagsoorten, 'df2': dagsoortenR}
    bestandendict = {'df1': 'results', 'df2': 'resultsref'}
    
    dagsoortdict = {'Ma' : 0, 'Di': 1, 'Wo': 2, 'Do': 3, 'Vr': 4, 'Za': 5, 'Zo': 6}

    for frame in ['df1', 'df2']:
        dat = datumsdict[frame]
        per = periodesdict[frame]
        dag = dagendict[frame]
        results = bestandendict[frame]
    
        frame = vdata[(vdata['datum'] >= dat[0]) & (vdata['datum'] <= dat[1])]
        frame = frame[(frame['uur'] >= int(per[0])) & (frame['uur'] < int(per[1]))]

        frame['vlag'] = 0
        for dagje in dag:
            frame.loc[(frame['weekdag'] == dagsoortdict[dagje]), 'vlag'] = 1
        frame = frame[frame['vlag'] == 1]
        
        frame = frame.drop(columns = ['timestamp', 'datum', 'weekdag', 'uur', 'vlag'])
        frame = frame.groupby(['naam']).mean().reset_index()
        
        frame = frame.astype({col: int for col in frame.columns[1:]})
        
        frame.to_sql(results, con, if_exists='replace', index = False)

    con.close()
    
    return bufferscale

def mappen(bufferscale):
    
    con = sqlite3.connect("vlogdashboard.sqlite")

    #con.enable_load_extension(True)
    #con.execute("SELECT load_extension('mod_spatialite')")

    sgs = pd.read_sql_query("SELECT * from mapping", con)
    sgs['link_id'] = sgs['link_id'].astype(int)
    df1 = pd.read_sql_query("SELECT * from results", con)
    df2 = pd.read_sql_query("SELECT * from resultsref", con)
    vrilijst = sgs['Naam'].unique()
    
    dfs = pd.DataFrame()
    for frame in [df1, df2]:
        results = 0
        if frame.equals(df1): results = 1
        for vri in vrilijst:
            try:
                df0 = frame[frame['naam'] == vri]
                df0 = df0.T
                df0.rename(columns={df0.columns[0]: 'int'}, inplace = True)
                df0 = df0[df0['int'] != vri]
                df0 = df0.reset_index()
                df0.rename(columns={'index':'SG'}, inplace = True)
                df0['SG'] = df0['SG'].astype(int)
        
                sg0 = sgs[sgs['Naam'] == vri]
                df = pd.merge(df0,sg0[['SG', 'link_id']], how = 'left', on = 'SG')
                df = df[df['link_id'].isna() == False]
                df = df.drop(columns = 'SG')
                df['results'] = results
                dfs = pd.concat([dfs,df], axis = 0, ignore_index = True)
            except:
                pass

    dfs = dfs.groupby(['results', 'link_id']).sum().reset_index()
    
    dfs.loc[(dfs['results'] ==1), 'int1'] = dfs['int']
    dfs.loc[(dfs['results'] ==0), 'int0'] = dfs['int']
    dfs = dfs.drop(columns = ['results', 'int'])

    # truc om de missings te behouden    
    dfs['link_id'] = dfs['link_id'].astype(int)
    dfs = dfs.groupby(['link_id']).sum(min_count=1).reset_index()

    # koppelen aan network_base
    # https://gist.github.com/perrygeo/868135514d2518257bbb

    #sql = "SELECT link_id,Hex(ST_AsBinary(GEOMETRY)) as geom FROM network_base;"
    #gdf = gpd.GeoDataFrame.from_postgis(sql, con, geom_col= 'geom')
    #gdf = gpd.read_postgis(sql, engine)
    #gdf.rename(columns={'geom': 'geometry'}, inplace = True)
    #gdf = gdf.set_geometry('geometry')
    
    zipfile = 'zip://network_base.zip'
    gdf = gpd.read_file(zipfile)

    gdf = gdf.set_crs(28992)
    
    dfs['link'] = dfs['link_id']
    dfs['link_id'] = abs(dfs['link_id'])
    
    
    gdf = pd.merge(gdf,dfs, how = 'right', on = 'link_id')
    gdf = gpd.GeoDataFrame(gdf, geometry = 'geometry')

    gdf = gdf.to_crs(4326)
    
    bounds = gdf.bounds
    minx = bounds['minx'].min() 
    miny = bounds['miny'].min() 
    maxx = bounds['minx'].max() 
    maxy = bounds['miny'].max()
    bounds = [[miny,minx],[maxy,maxx]]
    gdf = gdf.to_crs(28992)
    
    # klasses maken    
    gdf1 = gdf.copy()
    gdf1['klasse'] = 3
    gdf2 = gdf.copy()
    gdf2['klasse'] = 2
    
    gdf2['cum'] = 0

    gdf = pd.concat([gdf1, gdf2], axis=0, ignore_index=True) #Add the cluster series to your dataframe

    # klasse 3 is geel, klasse 2 is groen, klasse 1 is rood
    # renderen in volgorde van klasse

    # bij missing values
    gdf.loc[(gdf['int0'].isna() == True) | (gdf['int1'].isna() == True), 'klasse'] = 4
    gdf.loc[(gdf['int0'].isna() == True) & (gdf['int1'].isna() == False), 'int0'] = 0
    gdf.loc[(gdf['int0'].isna() == False) & (gdf['int1'].isna() == True), 'int1'] = 0
    
    gdf['int0'] = gdf['int0'].astype(int)
    gdf['int1'] = gdf['int1'].astype(int)


    # hier 80 cases
    
    gdf.loc[(gdf['int1'] < gdf['int0']) & (gdf['klasse'] == 3), 'cum'] = gdf['int1']
    gdf.loc[(gdf['int1'] < gdf['int0']) & (gdf['klasse'] == 2), 'cum'] = gdf['int0']

    gdf.loc[(gdf['int1'] < gdf['int0']) & (gdf['klasse'] == 4), 'cum'] = gdf['int0']

    gdf.loc[(gdf['int1'] >= gdf['int0']) & (gdf['klasse'] == 3), 'cum'] = gdf['int0']
    gdf.loc[(gdf['int1'] >= gdf['int0']) & (gdf['klasse'] == 2), 'klasse'] = 1
    gdf.loc[(gdf['int1'] >= gdf['int0']) & (gdf['klasse'] == 1), 'cum'] = gdf['int1']

    gdf.loc[(gdf['int1'] >= gdf['int0']) & (gdf['klasse'] == 4), 'cum'] = gdf['int1']
    
    gdf.loc[(gdf['link'] >0), 'buffie'] = - gdf['cum']/bufferscale
    gdf.loc[(gdf['link'] <0), 'buffie'] = gdf['cum']/bufferscale


    gdf['buffie'] = gdf['buffie'].astype(int)
    
    # corrigeren 0 buffies
    gdf.loc[(gdf['buffie'] ==0), 'buffie'] = 1

    gdf['geometry'] = gdf['geometry'].buffer(gdf['buffie'], single_sided=True)
    
    gdf = gdf.to_crs(4326)
    
    con.close()

    return gdf, bounds

    
def visualiseren(gdf, bounds):

    # bij gebruik rechtsreeks met Leaflet is een API key noodzakelijk
    Stadia_AlidadeSmoothDark = 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png?api_key=83fd135a-4500-4d47-9b73-ac8757d5eeed'
    attr= "<a href=https://stadiamaps.com/>Stadia Maps</a>"
    
    m = folium.Map(location=[51.557921, 5.083056], tiles = None, zoom_start = 50)
    folium.TileLayer(Stadia_AlidadeSmoothDark, attr = attr, name = "Stadia").add_to(m)
    m.fit_bounds(bounds)

    fg1 = folium.FeatureGroup(name='verschilplot', show=True)
    
    klas1 = gdf[gdf['klasse'] ==1]
    klas2 = gdf[gdf['klasse'] ==2]
    klas3 = gdf[gdf['klasse'] ==3]
    klas4 = gdf[gdf['klasse'] ==4]
    
    
    if len(klas1) >0:
        folium.GeoJson(klas1[['geometry', 'klasse', 'cum']],style_function=lambda x: {"weight":0.1,'color': 'red','fillColor': 'red', 'fillOpacity':1.0},
              highlight_function=lambda x: {'color':'white'},  smooth_factor=2.0,
              tooltip =  folium.features.GeoJsonTooltip(fields=['klasse', 'cum',], labels=True, sticky=True, toLocaleString=True)).add_to(fg1)
    if len(klas2) >0:
        folium.GeoJson(klas2[['geometry', 'klasse', 'cum']],style_function=lambda x: {"weight":0.1,'color': 'green','fillColor': 'green', 'fillOpacity':1.0},
              highlight_function=lambda x: {'color':'white'},  smooth_factor=2.0,
              tooltip =  folium.features.GeoJsonTooltip(fields=['klasse','cum'], labels=True, sticky=True, toLocaleString=True)).add_to(fg1)
    if len(klas3) >0:
        folium.GeoJson(klas3[['geometry', 'klasse', 'cum']],style_function=lambda x: {"weight":0.1,'color': 'yellow','fillColor': 'yellow', 'fillOpacity':1.0},
              highlight_function=lambda x: {'color':'white'},  smooth_factor=2.0,
              tooltip =  folium.features.GeoJsonTooltip(fields=['klasse','cum'], labels=True, sticky=True, toLocaleString=True)).add_to(fg1)
    if len(klas4) >0:
        folium.GeoJson(klas4[['geometry', 'klasse', 'cum']],style_function=lambda x: {"weight":0.1,'color': 'grey','fillColor': 'grey', 'fillOpacity':1.0},
              highlight_function=lambda x: {'color':'white'},  smooth_factor=2.0,
              tooltip =  folium.features.GeoJsonTooltip(fields=['klasse','cum'], labels=True, sticky=True, toLocaleString=True)).add_to(fg1)
    
    for fg in [fg1]:
          m.add_child(fg)

    
    folium.LayerControl(autoZIndex=False, collapsed=False).add_to(m) #Add layer control to toggle on/off

    # Display the Folium map using Streamlit
    map_container = folium_static(m,width=1500, height = 1000)
    map_container.markdown = f'<div class="map-container">{map_container.markdown}</div>'


def main():
    

    
    st.set_page_config(layout="wide")
    
    st.markdown("""
    <style>
        .main > div {
            padding-top: 0rem;
            padding-left: 0rem;
            padding-right: 0rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    #st.markdown(margins_css, unsafe_allow_html=True)
    
    st.sidebar.markdown("""
    <div style="background-color:#f0f0f0; border-radius:5px; padding:0px">
        <h1>Legenda</h1>
        <p><span style="color:yellow">&#9632;</span> Zelfde verkeer als in referentie</p>
        <p><span style="color:red">&#9632;</span> Meer verkeer dan in referentie</p>
        <p><span style="color:green">&#9632;</span> Minder verkeer dan in referentie</p>
        <p><span style="color:grey">&#9632;</span> Geen data</p>

    </div>
    """, unsafe_allow_html=True)
    
    
    bufferscale = maken_selecties()

    gdf, bounds = mappen(bufferscale)
    visualiseren(gdf, bounds)
    
    
if __name__ == "__main__":
    main()    


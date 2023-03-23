######################################
# Created on Fri Apr 17, 2022
#
#author: Aaron Paul
######################################

from dash import Dash, dash_table, html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

import pandas as pd
import numpy as np

import plotly.graph_objects as go
import plotly.express as px

# Meta_tags
meta_tags = [
    {
        "name": "viewport",
        "content": "width = device-width"
    }
]

# Define our app with stylesheets
app = Dash(__name__, external_stylesheets = [dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP], meta_tags = meta_tags)
app.title = "COVID-19 Live Tracker"

# Read the data
url_confirmed_global = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv"
url_deaths_global = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv"
url_recovered_global = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv"
confirmed_df = pd.read_csv(url_confirmed_global)
deaths_df = pd.read_csv(url_deaths_global)
recovered_df = pd.read_csv(url_recovered_global)
# This is used to control the map zoom level late
area_df = pd.read_csv("area.csv")
area_list = area_df.country.to_list()

# Unpivot (reshape) the data using the melt() function
confirmed_global = confirmed_df.melt(
    id_vars = ["Province/State", "Country/Region", "Lat", "Long"],
    value_vars = confirmed_df.columns[4:],
    var_name = "date",
    value_name = 'confirmed'
)
deaths_global = deaths_df.melt(
    id_vars = ["Province/State", "Country/Region", "Lat", "Long"],
    value_vars = deaths_df.columns[4:],
    var_name = "date",
    value_name = 'deaths'
)
recovered_global = recovered_df.melt(
    id_vars = ["Province/State", "Country/Region", "Lat", "Long"],
    value_vars = recovered_df.columns[4:],
    var_name = "date",
    value_name = 'recovered'
)
#################### Merge Datasets ####################
covid_merge = pd.merge(confirmed_global, deaths_global, on = ['Province/State', 'Country/Region', 'Lat', 'Long', 'date'], how = "left")
covid_merge = pd.merge(covid_merge, recovered_global, on = ['Province/State', 'Country/Region', 'Lat', 'Long', 'date'], how = "left")
covid_merge["date"] = pd.to_datetime(covid_merge["date"]) # Convert "Date to datetime type"
covid_merge["recovered"] = covid_merge["recovered"].fillna(0)
covid_merge["recovered"] = covid_merge["recovered"].astype(int)
# Active cases
covid_merge["active"] = covid_merge["confirmed"] - covid_merge["deaths"]- covid_merge["recovered"]

################################ Data Cleaning ######################
change_country_region = covid_merge[covid_merge["Province/State"].notnull()]
for index, row in change_country_region.iterrows():
  if row["Province/State"] in ["Diamond Princess", "Grand Princess", "Tibet"]:
    covid_merge['Country/Region'].at[index] = row["Province/State"] # update the row in the dataframe
  elif row["Country/Region"] in ["Denmark", "France", "Netherlands", "New Zealand", "United Kingdom"]:
    covid_merge['Country/Region'].at[index] = row["Province/State"] # update the row in the dataframe
replace_names = {
    "US": "USA",
    "Korea, South": "South Korea",
    "Korea, North": "North Korea",
    "Taiwan*": "Taiwan",
    "Burma": "Myanmar",
    "Holy See": "Vatican City",
    "Diamond Princess": "Cruise Ship",
    "MS Zaandam": "Cruise Ship",
    "Grand Princess": "Cruise Ship",
}
covid_merge["Country/Region"] = covid_merge["Country/Region"].replace(replace_names)
################################ Canada: Impute the values in "Lat" and "Long" ######################
condition1 = covid_merge["Country/Region"] == "Canada" 
canada_df = covid_merge.loc[condition1]
# We can use the mean function to impute the values in Lattitude and Longtitude.
canada_lat_mean = canada_df['Lat'].mean()
canada_long_mean = canada_df['Long'].mean()
# position of NaN values in terms of index
canada_nan = canada_df.loc[pd.isna(canada_df["Lat"]), :].index
# Update covid_merge DataFrame for missing "Lat" and "Long"
for index in canada_nan:
  covid_merge.loc[index, "Lat"] = canada_lat_mean
  covid_merge.loc[index, "Long"] = canada_long_mean
################################ China: Impute the values in "Lat" and "Long" ######################
condition2 = covid_merge["Country/Region"] == "China"
china_df = covid_merge.loc[condition2]
# We can use the mean function to impute the values in Lattitude and Longtitude.
china_lat_mean = china_df['Lat'].mean()
china_long_mean = china_df['Long'].mean()
# position of NaN values in terms of index
china_nan = china_df.loc[pd.isna(china_df["Lat"]), :].index
for index in china_nan:
  covid_merge.loc[index, "Lat"] = china_lat_mean
  covid_merge.loc[index, "Long"] = china_long_mean
# Final Dataset
covid_global = covid_merge.groupby(["date", "Country/Region"], as_index = False).agg(
    {
        "Lat": "mean",
        "Long": "mean",
        "confirmed": "sum",
        "deaths": "sum",
        "recovered": "sum",
        "active": "sum",
    }
)
# List of all countries (sorted)
country_list = covid_global["Country/Region"].sort_values(ascending=True).unique()
# Last Update
last_update = covid_global["date"].iloc[-1].strftime("%B %d, %Y")
# Global Cumulative for each day
daily_cum_global = covid_global.groupby(["date"])[['confirmed', 'deaths', 'recovered', 'active']].sum().reset_index()
# Global Totals
tot_confirmed_global = daily_cum_global["confirmed"].iloc[-1]
tot_deaths_global = daily_cum_global["deaths"].iloc[-1]
tot_recovered_global = daily_cum_global["recovered"].iloc[-1]
tot_active_global = daily_cum_global["active"].iloc[-1]
# New Global Cases, Deaths, Recovery, Active
new_confirmed_global = tot_confirmed_global - daily_cum_global["confirmed"].iloc[-2]
new_deaths_global = tot_deaths_global - daily_cum_global["deaths"].iloc[-2]
new_recovered_global = tot_recovered_global - daily_cum_global["recovered"].iloc[-2]
new_active_global = tot_active_global - daily_cum_global["active"].iloc[-2]
# Percentage of Previous Day
pct_change_confirmed = round((new_confirmed_global / daily_cum_global["confirmed"].iloc[-2]) * 100, 2)
pct_change_deaths = round((new_deaths_global / daily_cum_global["deaths"].iloc[-2]) * 100, 2)
pct_change_recovered = 0 if daily_cum_global["recovered"].iloc[-2] == 0 else round((new_recovered_global / daily_cum_global["recovered"].iloc[-2]) * 100, 2)
pct_change_active = round((new_active_global / daily_cum_global["active"].iloc[-2]) * 100, 2)

# Countries Lattest Totals
country_totals_df = covid_global.loc[covid_global["date"] == last_update].reset_index(drop = True)
dict_country_locations = country_totals_df.set_index("Country/Region")[["Lat", "Long"]].T.to_dict("dict")

# # default CSV
# csv_data = country_totals_df.to_csv()

# Navbar
navbar = dbc.Navbar(
    dbc.Container(
        children = [
            # Rows
            dbc.Row(
                children = [
                    dbc.Col(
                        children = [
                            # Image
                            html.Img(src = app.get_asset_url("coronavirus.svg"), height = "70px"),
                            # Brand
                            dbc.NavbarBrand(
                                "Covid-19 Analysis Dashboard",
                                style = {
                                    # "color": "black",
                                    "fontSize": "25px",
                                    "fontFamily": "Times New Roman"
                                },
                                className = "ms-2"
                            )
                        ],
                        width = {
                            "size": "auto"
                        }
                    )
                ],
                align = "center",
                className = "g-0",
            ),
            # Rows
            dbc.Row(
                children = [
                    dbc.Col(
                        children = [
                            dbc.Nav(
                                [
                                   dbc.NavItem(dbc.NavLink("Home", href = "/")),
                                   dbc.NavItem(dbc.NavLink("Link1", href = "/link1")),
                                   dbc.NavItem(dbc.NavLink("Link2", href = "/link2")),
                                   dbc.NavItem(
                                       dbc.DropdownMenu(
                                           children = [
                                               dbc.DropdownMenuItem("More pages", header = True),
                                               dbc.DropdownMenuItem("Link3", href = "/link3")
                                           ],
                                           nav = True,
                                           in_navbar = True,
                                           label = "More"
                                       )
                                   )
                                ],
                                navbar = True
                            )
                        ],
                        width = {
                            "size": "auto"
                        }
                    )
                ],
                align = "center",
                # style = {
                #     "textAlign": "center",
                #     "marginTop": 30,
                #     "marginBottom": 30,
                #     "color": "purple"
                # }
            ),
            # Add a toggler
            dbc.Col(dbc.NavbarToggler(id="navbar-toggler", n_clicks=0)),
            # Rows
            dbc.Row(
                children = [
                    dbc.Col(
                        children = [
                            dbc.Collapse(
                                dbc.Nav(
                                    [
                                        dbc.NavItem(dbc.NavLink(html.I(className = "bi bi-github"), href = "https://github.com/lewisaaronpaul", external_link = True)),
                                        dbc.Input(type="search", placeholder="Search"),
                                        dbc.Button(
                                            "Search", color="primary", className="ms-2", n_clicks=0
                                        ),
                                    ],
                                    # navbar = True
                                ),
                                id = "navbar-collapse",
                                is_open = False,
                                navbar = True
                            )    
                        ],
                        # width = {
                        #     "size": "auto"
                        # }
                    )
                ],
                align = "center",
                # style = {
                #     "textAlign": "center",
                #     "marginTop": 30,
                #     "marginBottom": 30,
                #     "color": "purple"
                # }
            ),
            
        ],
        fluid = True
    ),
    color = "purple",
    dark = True
) # End navbar

# The Marquee Container
marquee = dbc.Container(
    # Rows
    [
        # Marquee Row
        dbc.Row(
            children = [
                # Rolling text
                html.Marquee(
                    id = "marquee", 
                    children = f"Last Update: {last_update}",
                )
            ],
            style = {
                "color": "orange",
                "fontWeight": "bold",
                "padding": "10px",
                "backgroundColor": "white"
            },
            
        ), # End Marquee Row
        # html.Br(),
        # html.Br(),
    ], 
    fluid = True,
)

# Total Cards
card_layout = html.Div(
    id = "cards",
    className = "row flex-display",
    children = [
        # Card #1
        # Global Cases
        html.Div(
            id = "card-one",
            className = "card-container three columns",
            children = [
                html.H6(
                    "Global Cases",
                    style = {
                        "textAlign": "center",
                        "color": "white",
                        "fontWeight": "bold"
                    }    
                ),
                html.P(
                    f"{tot_confirmed_global:,}",
                    style = {
                        "textAlign": "center",
                        "color": "orange",
                        "fontSize": "40px"
                    },
                ),
                html.P(
                    f"New: {new_confirmed_global:,}   ({pct_change_confirmed}%)",
                    style = {
                        "textAlign": "center",
                        "color": "orange",
                        "fontSize": "15px",
                        "marginTop": "-18px"
                    }    
                ),
            ]
        ), # End Card #1
        # Card #2
        # Global Deaths
        html.Div(
            id = "card-two",
            className = "card-container three columns",
            children = [
                html.H6(
                    "Global Deaths",
                    style = {
                        "textAlign": "center",
                        "color": "white",
                        "fontWeight": "bold"
                    }    
                ),
                html.P(
                    f"{tot_deaths_global:,}",
                    style = {
                        "textAlign": "center",
                        "color": "#dd1e35",
                        "fontSize": "40px"
                    },
                ),
                html.P(
                    f"New: {new_deaths_global:,}   ({pct_change_deaths}%)",
                    style = {
                        "textAlign": "center",
                        "color": "#dd1e35",
                        "fontSize": "15px",
                        "marginTop": "-18px"
                    }    
                ),
            ]
        ), # End Card #2
        # Card #3
        # Global Recovered
        html.Div(
            id = "card-three",
            className = "card-container three columns",
            children = [
                html.H6(
                    "Global Recovered",
                    style = {
                        "textAlign": "center",
                        "color": "white",
                        "fontWeight": "bold"
                    }    
                ),
                html.P(
                    f"{tot_recovered_global:,}",
                    style = {
                        "textAlign": "center",
                        "color": "#7CFC00",
                        "fontSize": "40px"
                    },
                ),
                html.P(
                    f"New: {new_recovered_global:,}   ({pct_change_recovered}%)",
                    style = {
                        "textAlign": "center",
                        "color": "#7CFC00",
                        "fontSize": "15px",
                        "marginTop": "-18px"
                    }    
                ),
            ]
        ), # End Card #3
        # Card #4
        # Global Active
        html.Div(
            id = "card-four",
            className = "card-container three columns",
            children = [
                html.H6(
                    "Global Active",
                    style = {
                        "textAlign": "center",
                        "color": "white",
                        "fontWeight": "bold"
                    }    
                ),
                html.P(
                    f"{tot_active_global:,}",
                    style = {
                        "textAlign": "center",
                        "color": "#e55467",
                        "fontSize": "40px"
                    },
                ),
                html.P(
                    f"New: {new_active_global:,}   ({pct_change_active}%)",
                    style = {
                        "textAlign": "center",
                        "color": "#e55467",
                        "fontSize": "15px",
                        "marginTop": "-18px"
                    }    
                ),
            ]
        ), # End Card #4
    ]
)

def make_kpi(new_today, new_yesterday, color, title):
    indicator = {
        "data": [
            go.Indicator(
                mode = "number+delta",
                value = new_today,
                delta = {
                    "reference": new_yesterday,
                    "position": "right",
                    "valueformat": ",.0f",
                    "relative": False,
                    "font": {
                        "size": 15
                    }
                },
                number = {
                    "valueformat": ",",
                    "font": {
                        "size": 20
                    }
                },
                domain = {
                    "y": [0, 1],
                    "x": [0, 1]
                }  
            )
        ],
        "layout": go.Layout(
            title = {
                "text": title,
                "y": 1,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top"
            },
            font = dict(color = color),
            paper_bgcolor = "#1f2c56",
            plot_bgcolor = "#1f2c56",
            height = 50,
        )
    }
    
    return indicator

# Pie Chart
def make_pie_chart(country, confirmed, deaths, recovered, active, colors):
    figure = {
        "data": [
            go.Pie(
                labels = ["<b>Confirmed</b>", "<b>Deaths</b>", "<b>Recovered</b>", "<b>Active</b>"],
                values = [confirmed, deaths, recovered, active],
                marker = dict(colors = colors),
                hoverinfo = "label+value+percent",
                textinfo = "label+value",
                hole = 0.7,
                rotation = 45,
                # insidetextorientation = "radial"
            )
        ],
        "layout": go.Layout(
            title = {
                "text": f"Totals Cases: {country}",
                "y": 0.93,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top"
            },
            titlefont = {
                "color": "white",
                "size": 20
            },
            font = dict(
                family = "sans-serif",
                color = "white",
                size = 12
            ),
            hovermode = "closest",
            paper_bgcolor = "#1f2c56",
            plot_bgcolor = "#1f2c56",
            legend = {
                "orientation": "h",
                "bgcolor": "#1f2c56",
                "y": -0.7,
                "x": 0.5,
                "xanchor": "center",
            }
        )
    }
    
    return figure

# Create Bar and Line Charts
def make_bar_line_chart(country, df, x, y):
    figure = {
        "data": [
            go.Bar(
                name = "Daily Confirmed Cases",
                x = df[x],
                y = df[y], 
                # text = df[y],
                customdata = df.values,
                hovertemplate = "<br>".join(["<b>%{customdata[0]}</b>",
                                        "Date: %{customdata[1]|%b %d, %Y}",
                                        "Daily Confirmed: %{customdata[4]:,}",
                                        "Daily Deaths: %{customdata[5]:,}",
                                        "Total Confirmed: %{customdata[2]:,}",
                                        "Total Deaths: %{customdata[3]:,}",
                                        "<extra></extra>"]),
                marker = dict(color = "orange"),
            ),
            go.Scatter(
                name = "7 Day Rolling Average: Daily Confirmed",
                x = df[x],
                y = df["rolling_average"], 
                mode = "lines",
                # text = df[y],
                customdata = df.values,
                hovertemplate = "<br>".join(["<b>%{customdata[0]}</b>",
                                        "<b>Date</b>: %{customdata[1]|%b %d, %Y}",
                                        "<b>Rolling Avg. Confirmed</b>: %{customdata[6]:,.0f}",
                                        "<b>Daily Confirmed</b>: %{customdata[4]:,}",
                                        "<extra></extra>"]),
                line = dict(
                    width = 3,
                    color = "#FF00FF",
                ),
            )
        ],
        "layout": go.Layout(
            title = {
                "text": f"{country}: Last 356 Days",
                "y": 0.93,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top"
            },
            titlefont = {
                "color": "white",
                "size": 20
            },
            font = dict(
                family = "sans-serif",
                color = "white",
                size = 12
            ),
            hovermode = "closest",
            paper_bgcolor = "#1f2c56",
            plot_bgcolor = "#1f2c56",
            legend = {
                "orientation": "h",
                "bgcolor": "#1f2c56",
                "y": -0.7,
                "x": 0.5,
                "xanchor": "center",
            },
            margin = dict(
                r = 0,
            ),
            xaxis = dict(
                title = "<b>Date</b>",
                color = "white",
                showline = True,
                showgrid = True,
                showticklabels = True,
                linecolor = "white",
                linewidth = 1,
                ticks = "outside",
                tickfont = dict(
                    family = "Arial",
                    color = "white",
                    size = 12
                ),
            ),
            yaxis = dict(
                title = "<b>Daily Confirmed Cases</b>",
                color = "white",
                showline = True,
                showgrid = True,
                showticklabels = True,
                linecolor = "white",
                linewidth = 1,
                ticks = "outside",
                tickfont = dict(
                    family = "Arial",
                    color = "white",
                    size = 12
                ),
            ),
        )
    }
    
    return figure

# Create Scatter Plot on Mapbox
def make_map_chart(df, zoom, zoom_lat, zoom_long):
    figure = {
        "data": [
            go.Scattermapbox(
                name = "Country Totals",
                lon = df["Long"],
                lat = df["Lat"],
                mode = "markers",
                marker = go.scattermapbox.Marker(
                    size = df["confirmed"]/80000,
                    sizemin = 10,
                    # sizeref = 0.00001,
                    color = (df["confirmed"] - df["confirmed"].min()) / (df["confirmed"].max() - df["confirmed"].min()),
                    colorscale = [ [0, "#7CFC00"], [0.00018, "yellow"], [0.00091, "rgb(255, 0, 255)"], [0.0046, "turquoise"],[0.0098, "royalblue"],[0.043, "purple"], [0.5, "#e55467"], [1.0, "rgb(255, 0, 0)"]],
                    showscale = True,
                    sizemode = "area",
                    opacity = 0.6
                ),
                customdata = df.values,
                hovertemplate = "<br>".join(["<b>%{customdata[1]}</b>",
                                        "<b>Latitude:</b> %{customdata[2]}",
                                        "<b>Longitude:</b> %{customdata[3]}",
                                        "<b>Total Confirmed:</b> %{customdata[4]:,}",
                                        "<b>Total Deaths:</b> %{customdata[5]:,}",
                                        "<b>Total Recovered:</b> %{customdata[6]:,}",
                                        "<b>Total Active:</b> %{customdata[7]:,}",
                                        "<b>Date:</b> %{customdata[0]|%b %d, %Y}",
                                        "<extra></extra>"]),
                # showlegend = True
            ),
            
        ],
        "layout": go.Layout(
            hovermode = "closest",   #"closest",x
            paper_bgcolor = "#1f2c56",
            plot_bgcolor = "#1f2c56",
            font = dict(
                family = "sans-serif",
                color = "white",
                size = 12
            ),
            # legend = {
            #     "orientation": "h",
            #     "bgcolor": "#1f2c56",
            #     "y": -0.7,
            #     "x": 0.5,
            #     "xanchor": "center",
            # },
            margin = dict(
                r = 0,
                l = 0,
                b = 0,
                t = 0
            ),
            mapbox = dict(
                accesstoken = "pk.eyJ1IjoibGV3aXNhYXJvbnBhdWwiLCJhIjoiY2tlOWhmZ3JsMDRrcDJzcDk0cTB3d2l2dCJ9.Lu9ycajydSHstZm9mw_oDg",
                center = go.layout.mapbox.Center(
                    lat = zoom_lat,  # Change for each selected country
                    lon = zoom_long,  # Change for each selected country
                ),
                style = "dark",#"open-street-map",#"stamen-terrain",#"carto-positron",#"dark",
                zoom = zoom,  # Change for each selected country
            ),
            autosize = True,
            # height = 900,
            # width = 1600      
        )
    }
    
    return figure # End Map Chart

# Country Information
country_info = html.Div(
    className = "row flex-display",
    children = [
        # Create KPI's
        html.Div(
            className = "create-container three columns",
            children = [
                html.P(
                    className = "fix-label",
                    children = ["Select Country:"],
                    style = {
                        "color": "white",
                    }    
                ),
                # Country Dropdown
                dcc.Dropdown(
                    id = "country-dropdown",
                    className = "dcc-component",
                    multi = False,
                    searchable = True,
                    options = [
                        {"label": country, "value": country} for country in country_list  #covid_global["Country/Region"].unique()
                    ],
                    value = "Belize",
                    placeholder = "Select a Country.",
                ),
                # Country New Cases
                html.P(
                    id = "country-last-update",
                    className = "fix-label",
                    # children = [
                    #     f"New Cases: {last_update}"
                    # ],
                    style = {
                        "textAlign": "center",
                        "color": "white",
                    }    
                ),
                # Confirmed KPI
                dcc.Graph(
                    id = "confirmed-kpi",
                    className = "dcc-component",
                    config = {
                        "displayModeBar": False
                    },
                    style = {
                        "margin-top": "20px",
                    }
                ),
                # Deaths KPI
                dcc.Graph(
                    id = "deaths-kpi",
                    className = "dcc-component",
                    config = {
                        "displayModeBar": False
                    },
                    style = {
                        "margin-top": "20px",
                    }
                ),
                # Recovery KPI
                dcc.Graph(
                    id = "recovery-kpi",
                    className = "dcc-component",
                    config = {
                        "displayModeBar": False
                    },
                    style = {
                        "margin-top": "20px",
                    }
                ),
                # Active KPI
                dcc.Graph(
                    id = "active-kpi",
                    className = "dcc-component",
                    config = {
                        "displayModeBar": False
                    },
                    style = {
                        "margin-top": "20px",
                    }
                ),
            ]
        ), 
        # Create Pie Chart for Country Totals
        html.Div(
            className = "create-container four columns",
            children = [
                # Pie Chart
                dcc.Graph(
                    id = "pie-chart",
                    config = {
                        "displayModeBar": "hover"
                    }
                ),
            ]
        ),
        # Add Bar and Line Charts
        html.Div(
            id = "bar-line",
            className = "create-container five columns",
            children = [
                # Bar and line Chart
                dcc.Graph(
                    id = "bar-line-chart",
                    config = {
                        "displayModeBar": "hover"
                    }
                ),
            ]
        ),
    ]
)

# Map Information
map_info = html.Div(
    className = "row flex-display",
    children = [
        # Add Map
        html.Div(
            className = "create-container-map twelve columns",
            children = [
                # Bar Chart
                dcc.Graph(
                    id = "map-chart",
                    config = {
                        "displayModeBar": "hover"
                    }
                ),
            ]
        ),
    ]
)

# HTML Body
app.layout = html.Div(
    id = "parent",
    children = [
        navbar,
        marquee,
        card_layout,
        country_info,
        map_info
    ],
    # style = {
    #     "display": "flex",
    #     "flex-direction": "column"
    # }
)

# Navbar Callback
# add callback for toggling the collapse on small screens
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

# Country Callback
@app.callback(
    Output(
        component_id = "country-last-update", # What will be updated
        component_property = "children"
    ),
    Output(
        component_id = "confirmed-kpi", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "deaths-kpi", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "recovery-kpi", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "active-kpi", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "pie-chart", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "bar-line-chart", # What will be updated
        component_property = "figure"
    ),
    Output(
        component_id = "map-chart", # What will be updated
        component_property = "figure"
    ),
    Input( 
        component_id = "country-dropdown", # Info coming from
        component_property = "value"
    )
)
def country_kpi(country):
    # Country Data
    country_data = covid_global[covid_global["Country/Region"] == country]
    tot_confirmed = country_data["confirmed"].iloc[-1]
    tot_deaths = country_data["deaths"].iloc[-1]
    tot_recovered = country_data["recovered"].iloc[-1]
    tot_active = country_data["active"].iloc[-1]
    # Yesterday's total
    tot_confirmed_yesterday = country_data["confirmed"].iloc[-2]
    tot_deaths_yesterday = country_data["deaths"].iloc[-2]
    tot_recovered_yesterday = country_data["recovered"].iloc[-2]
    tot_active_yesterday = country_data["active"].iloc[-2]
    # Today New: Cases, Deaths, Recovery, Active
    new_confirmed = tot_confirmed - tot_confirmed_yesterday
    new_deaths = tot_deaths - tot_deaths_yesterday
    new_recovered = tot_recovered - tot_recovered_yesterday
    new_active = tot_active - tot_active_yesterday
    # Yesterday New: Cases, Deaths, Recovery, Active
    yesterday_new_confirmed = tot_confirmed_yesterday - country_data["confirmed"].iloc[-3]
    yesterday_new_deaths = tot_deaths_yesterday - country_data["deaths"].iloc[-3]
    yesterday_new_recovered = tot_recovered_yesterday - country_data["recovered"].iloc[-3]
    yesterday_new_active = tot_active_yesterday - country_data["active"].iloc[-3]
    # Date of last update by Country
    country_date_text = f"New Cases: {last_update}"
    # Colors for Pie Chart
    colors = ["orange", "#dd1e35", "#7CFC00", "#e55467"]
    # Compute Daily Cases for each Country
    country_daily_data = country_data.loc[:, ["Country/Region", "date", "confirmed", "deaths"]]
    country_daily_data["daily_confirmed"] = country_daily_data["confirmed"] - country_daily_data["confirmed"].shift(1)
    country_daily_data["daily_confirmed"] = country_daily_data["daily_confirmed"].fillna(0)
    country_daily_data["daily_confirmed"] = country_daily_data["daily_confirmed"].astype(int)
    country_daily_data["daily_deaths"] = country_daily_data["deaths"] - country_daily_data["deaths"].shift(1)
    country_daily_data["daily_deaths"] = country_daily_data["daily_deaths"].fillna(0)
    country_daily_data["daily_deaths"] = country_daily_data["daily_deaths"].astype(int)
    # 7-Day Rolling Average
    country_daily_data["rolling_average"] = country_daily_data["daily_confirmed"].rolling(window = 7).mean()
    # Scattermapbox: zoom control information
    # Use the area of each country to control the zoom level
    if country in area_list:  #country == "Belize":
        area = area_df.loc[area_df.country == country, "areasqmi"].values[0]
        slope = (3 - 7) / (3800000 - 8900)
        zoom = 7 + slope * (area - 8900)
        zoom_lat = dict_country_locations[country]["Lat"]
        zoom_long = dict_country_locations[country]["Long"]
    else:
        zoom = 7    
        zoom_lat = dict_country_locations[country]["Lat"]
        zoom_long = dict_country_locations[country]["Long"]
    
    return country_date_text, \
        make_kpi(new_confirmed, yesterday_new_confirmed, "orange", "<b>New Confirmed</b>"),\
        make_kpi(new_deaths, yesterday_new_deaths, "#dd1e35", "<b>New Deaths</b>"),\
        make_kpi(new_recovered, yesterday_new_recovered, "#7CFC00", "<b>New Recovered</b>"),\
        make_kpi(new_active, yesterday_new_active, "#e55467", "<b>New Active</b>"),\
        make_pie_chart(country, tot_confirmed, tot_deaths, tot_recovered, tot_active, colors),\
        make_bar_line_chart(country, country_daily_data.tail(365), "date", "daily_confirmed"),\
        make_map_chart(country_totals_df, zoom, zoom_lat, zoom_long)
        
if __name__ == '__main__':
    app.run(debug=False)
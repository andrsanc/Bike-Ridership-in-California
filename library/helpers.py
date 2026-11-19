# Function to plot stations on a map
def station_plot_fun(df, lat, lon, w, h, z, cm):
    df = df.rename(columns = {lat: 'lat', lon: 'lon'})
    f = folium.Figure(width = w, height = h)
    m = folium.Map(location = [df['lat'].mean(), df['lon'].mean()],
                   zoom_start = z).add_to(f)
    for row in df.dropna(subset = ['lat', 'lon']).itertuples():
        c = cm.get(row.station_region, "gray") 
        folium.CircleMarker(location = [row.lat, row.lon],
                            radius = 4,
                            fill = True,
                            color = c,
                            fill_color = c,
                            fill_opacity = 0.8).add_to(m)
    return f

# Function to get distance from latitudes and longitudes
def distance_fun(lat_1, lon_1, lat_2, lon_2):
    lon_1, lat_1, lon_2, lat_2 = map(math.radians, [lon_1, lat_1, lon_2, lat_2])
    dlon = lon_2 - lon_1
    dlat = lat_2 - lat_1
    a = math.sin(dlat/2)**2 + math.cos(lat_1) * math.cos(lat_2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    d = c * r * 0.62137119224
    return(d)

# Function to impute missing coordinates
def missing_coord_fun(df, coord_df, s):
    coord_df = coord_df[['station_id', 'station_region', 'station_lat', 'station_lon']]

    if s == 'start':
        df = df.merge(coord_df, left_on = ['start_station_id'], right_on = ['station_id'], how = 'inner')
        df.loc[df['start_lat'].isnull(), 'start_lat'] = df['station_lat']
        df.loc[df['start_lon'].isnull(), 'start_lon'] = df['station_lon']
        df = df.rename(columns = {'station_region': 'start_region'})
        
    elif s == 'end':
        df = df.merge(coord_df, left_on = ['end_station_id'], right_on = ['station_id'], how = 'inner')
        df.loc[df['end_lat'].isnull(), 'end_lat'] = df['station_lat']
        df.loc[df['end_lon'].isnull(), 'end_lon'] = df['station_lon']
        df = df.rename(columns = {'station_region': 'end_region'})

    df = df.drop(['station_id', 'station_lat', 'station_lon'], axis = 1)

    return df

# Function to get coordinates of all stations
def station_coord_fun(df):
    start_df = pd.DataFrame({'station_region': df['start_region'],
                             'station_id': df['start_station_id'],
                             'station_lat': df['start_lat'],
                             'station_lon': df['start_lon']})
    end_df = pd.DataFrame({'station_region': df['end_region'],
                           'station_id': df['end_station_id'],
                           'station_lat': df['end_lat'],
                           'station_lon': df['end_lon']})
    df = pd.concat([start_df, end_df])
    df = df[df['station_lat'].isnull() == False]
    for c in ['station_lat', 'station_lon']:
        df[c] = df[c].astype(float)
    df = df\
        .groupby(['station_region', 'station_id'], as_index = False)\
        .agg(station_lat = ('station_lat', 'mean'),
             station_lon = ('station_lon', 'mean'))
    return df

# Function to append county from geometry
def county_geo_fun(df, latc, lonc, geodf):
    points = gpd.GeoDataFrame(df,
                              geometry = gpd.points_from_xy(df[lonc], df[latc]),
                              crs = 'EPSG:4326')

    geodf.columns = ['station_region', 'geometry']
    geo_df = gpd.sjoin(points,
                       geodf,
                       how = 'left',
                       predicate = 'within')
    df['station_region'] = geo_df['station_region']
    
    return df
    
# Function to append federal holidays
def federal_holiday_fun(df):
    start_date = df['date'].min()
    end_date = df['date'].max()
    # Days
    days_df = pd.DataFrame({'date': pd.date_range(start_date, periods = (end_date - start_date).days + 1)})
    days_df['year'] = [d.year for d in days_df['date']]
    days_df['month'] = [d.month for d in days_df['date']]
    days_df['day'] = [d.day for d in days_df['date']]
    days_df['weekday'] = [d.strftime('%A') for d in days_df['date']]
    days_df = days_df\
        .sort_values(by = ['year', 'month', 'weekday', 'date'], ascending = [True, True, True, True])\
        .reset_index(drop = True)
    days_df['wd_num_asc'] = days_df.groupby(['year', 'month', 'weekday']).cumcount()+1
    days_df = days_df\
        .sort_values(by = ['year', 'month', 'weekday', 'date'], ascending = [True, True, True, False])\
        .reset_index(drop = True)
    days_df['wd_num_desc'] = days_df.groupby(['year', 'month', 'weekday']).cumcount()+1
    days_df = days_df.sort_values(by = ['date'], ascending = [True])
    
    # Holidays
    days_df.loc[(days_df['month'] == 1) & (days_df['day'] == 1), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_asc'] == 3) & 
        (days_df['weekday'] == 'Monday') & 
        (days_df['month'] == 1), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_asc'] == 3) & 
        (days_df['weekday'] == 'Monday') & 
        (days_df['month'] == 2), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_desc'] == 1) & 
        (days_df['weekday'] == 'Monday') & 
        (days_df['month'] == 5), 'holiday'] = 1
    days_df.loc[(days_df['month'] == 6) & (days_df['day'] == 19), 'holiday'] = 1
    days_df.loc[(days_df['month'] == 7) & (days_df['day'] == 4), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_asc'] == 1) & 
        (days_df['weekday'] == 'Monday') & 
        (days_df['month'] == 9), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_asc'] == 2) & 
        (days_df['weekday'] == 'Monday') & 
        (days_df['month'] == 10), 'holiday'] = 1
    days_df.loc[(days_df['month'] == 11) & (days_df['day'] == 11), 'holiday'] = 1
    days_df.loc[(days_df['wd_num_asc'] == 4) & 
        (days_df['weekday'] == 'Thursday') & 
        (days_df['month'] == 11), 'holiday'] = 1
    days_df.loc[(days_df['month'] == 12) & (days_df['day'] == 25), 'holiday'] = 1
    days_df['holiday'] = days_df['holiday'].fillna(0).astype(int)
    days_df = days_df[['date', 'holiday']]
    df = df\
        .merge(days_df)\
        .reset_index(drop = True)
    return df

# Describe stats
def iqr_fun(df, c, f):   
    # describe() stats
    df = df[[c]]
    describe_df = df[c].describe()
    min_x = describe_df['min']
    max_x = describe_df['max']
    q1 = describe_df['25%']
    q3 = describe_df['75%']
    mean_x = describe_df['mean']
    median_x = describe_df['50%']
    # Outliers
    bottom_lim = max(min_x, q1 - 1.5 * (q3 - q1))
    bottom_outlier = df[df[c] < bottom_lim][c].max()
    is_bottom_outlier = df[c] < bottom_outlier
    top_lim = min(max_x, q3 + 1.5 * (q3 - q1))
    top_outlier = df[df[c] > top_lim][c].min()
    is_top_outlier = df[c] > top_outlier
    is_outlier = np.logical_or(is_bottom_outlier, is_top_outlier)
    # Skewness
    if mean_x > median_x:
        skew_x = 'Right Skew. Mean (' + format(mean_x, f) + ') > Median (' + format(median_x, f) + ')'
    else:
        skew_x = 'Left Skew. Mean (' + format(mean_x, f) + ') < Median (' + format(median_x, f) + ')'
    
    d = {'Skew': skew_x, 
         'IQR': format(q1, f) + ' thru ' + format(q3, f),
         'Range': format(min_x, f) + ' thru ' + format(max_x, f),
         'Outlier Range': format(bottom_outlier, f) + ' thru ' + format(top_outlier, f),
         'Outlier %': format(sum(is_outlier) / df.shape[0], ',.1%')}
    print(pd.Series(d).to_string())
    return sum(is_outlier)

# EDA histogram
def eda_hist_fun(d):    
    df = d['data']
    x = d['column']
    fig_num = d['title']    
    # Format for x-axis
    format_label = d['format']
    x_format = '{x:' + format_label + '}'
    # Bins 
    bin_num = d['bin_num']
    skew_y = max(pd.cut(df[x].tolist(), bins = bin_num).value_counts().tolist())
    # Histogram
    fig, ax = plt.subplots(figsize = d['figsize'])
    sns.histplot(df[x], kde = True, bins = bin_num, ax = ax)
    ax.set_title(fig_num, fontsize = 16, fontweight = 'bold', color = '#A51C30')
    ax.tick_params(axis = 'x', bottom = True, top = True, labelbottom = True, labeltop = False)
    ax.set_xlabel(x.replace('_', ' '), axis_font_dict)
    ax.set_ylabel('Density', axis_font_dict)
    ax.tick_params(axis = 'y', left = False, labelleft = False)
    ax.xaxis.set_major_formatter(x_format)
    plt.show()

# EDA violin plot
def eda_violin_fun(d):
    fig, ax = plt.subplots(figsize = d['figsize'])
    ax.set_title(d['title'], fontsize = 16, fontweight = 'bold', color = '#A51C30')
    if 'group' in d:
        sns.violinplot(x = d['x'], y = d['y'], hue = d['group'], data = d['data'], split = True)
    else:
        sns.violinplot(x = d['x'], y = d['y'], data = d['data'])
    plt.grid(axis = 'y')
    ax.set_xlabel(d['x'].replace('_', ' '), axis_font_dict)
    ax.set_ylabel(d['y'].replace('_', ' '), axis_font_dict)
    ax.yaxis.set_major_formatter(d['format'])
    plt.show()

# EDA scatter plot
def eda_scatter_fun(d):
    fig, ax = plt.subplots(figsize = d['figsize']) 
    ax.set_title(d['title'], fontsize = 16, fontweight = 'bold', color = '#A51C30')
    if 'group' in d:
        sns.scatterplot(x = d['x'], y = d['y'], hue = d['group'], data = d['data'], s = 5, alpha = 0.2)
    else:
        sns.scatterplot(x = d['x'], y = d['y'], data = d['data'], s = 5, alpha = 0.2)
    plt.grid(axis = 'y')
    ax.set_xlabel(d['x'].replace('_', ' '), axis_font_dict)
    ax.set_ylabel(d['y'].replace('_', ' '), axis_font_dict)
    ax.yaxis.set_major_formatter(d['format'])
    ax.legend(loc = 'upper right')
    plt.show()

# Function to return most popular station to station routes
def station_to_station_fun(df, region, top_n):
    df = df[df['trip_route_category'] == 'One Way'].reset_index(drop = True)
    if region in ['SoCal', 'NorCal']:
        df = df[df['cal_region'] == region].reset_index(drop = True)
    elif region in ['San Francisco', 'Alameda', 'DTLA', 'Westside', 'Santa Clara', 'Unknown', 'North Hollywood', 'San Mateo']:
        df = df[df['start_region'] == region].reset_index(drop = True)
    else:
        df = pd.DataFrame()
    df = df\
        .groupby(['cal_region', 'start_region', 'start_station_id', 'end_station_id'], as_index = False)\
        .agg(start_lat = ('start_lat', 'mean'),
             start_lon = ('start_lon', 'mean'),
             end_lat = ('end_lat', 'mean'),
             end_lon = ('end_lon', 'mean'),
             trips = ('trip', 'sum'))\
        .sort_values(by = 'trips', ascending = False)\
        .reset_index(drop = True)
    df['plot_region'] = region
    df = df.head(top_n).reset_index(drop = True)  
    return df

# # Function to plot the most popular station to station routes
# def station_to_station_plot_fun(df, num_cols, num_rows, w, h):
#     df['plot_lat'] = (df['start_lat'] + df['end_lat']) / 2
#     df['plot_lon'] = (df['start_lon'] + df['end_lon']) / 2
#     top_n = df.shape[0]
#     #region = df['plot_region'].iloc[0]
#     region = ', '.join(sorted(set(df['plot_region'])))
#     print('Top ' + str(top_n) + ' Station-to-Station Routes in ' + region + '\n')
#     # Plot
#     fig = Figure(width = w, height = h)
#     for i, row in enumerate(df.itertuples(), start = 1):
#         m = folium.Map(location = [row.plot_lat, row.plot_lon],
#                        zoom_start = 13)
#         line = folium.PolyLine(locations=[[row.start_lat, row.start_lon], [row.end_lat, row.end_lon]],
#                                color = 'blue', 
#                                weight = 5, opacity = 0.8).add_to(m)
#         PolyLineTextPath(line, '►', 
#                          repeat = True, 
#                          attributes = {'font-size': '18'}).add_to(m)
#         fig.add_subplot(num_rows, num_cols, i).add_child(m)    
#     return fig

# Function to plot the most popular station to station routes
def station_to_station_plot_fun(df, num_cols, num_rows, w, h):
    top_n = df.shape[0]
    region = ', '.join(sorted(set(df['plot_region'])))
    print('Top ' + str(top_n) + ' Station-to-Station Routes in ' + region + '\n')

    cell_w, cell_h = w // num_cols, h // num_rows
    cells = []
    for row in df.itertuples():
        start = [row.start_lat, row.start_lon]
        end = [row.end_lat, row.end_lon]

        m = folium.Map(location = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2],
                       zoom_start = 13,
                       width = cell_w, height = cell_h)
        line = folium.PolyLine([start, end],
                               color = 'blue',
                               weight = 5, 
                               opacity = 0.8).add_to(m)
        PolyLineTextPath(line, 
                         '►',
                         repeat = True,
                         attributes = {'font-size': '18'}).add_to(m)
        m.fit_bounds([start, end], padding = (30, 30))

        page = m.get_root().render()
        cells.append(f'<iframe srcdoc="{html.escape(page, quote=True)}" '
                     f'width="{cell_w}" height="{cell_h}" '
                     f'style="border:0; display:block;"></iframe>')
    grid = (f'<div style="display:grid; '
            f'grid-template-columns: repeat({num_cols}, {cell_w}px); gap:4px;">'
            + ''.join(cells) + '</div>')
    return HTML(grid)

# EDA Plot for categorical variables
def eda_bar_fun(d):
    x = d['column']
    df = d['data']\
        .groupby([x], as_index = False)\
        .agg(count = ('trip', 'sum'))\
        .sort_values('count', ascending = False)

    gs = gridspec.GridSpec(1, 1)
    pl.figure(figsize = d['figsize'])
    plt.suptitle(d['title'], fontsize = 16, fontweight = 'bold', color = '#A51C30')
    # Bar plot
    ax = pl.subplot(gs[0, 0])
    sns.barplot(data = df, x = x, y = 'count')
    for container in ax.containers:
        ax.bar_label(container, fmt = d['format'], fontweight = 'bold') 
    plt.ylabel('Count', axis_font_dict)
    plt.xlabel(x, axis_font_dict)
    return(gs)

# Function to plot residuals and QQ Plot
def plot_resid_fun(d):
    gs = gridspec.GridSpec(2, 2)
    pl.figure(figsize = d['figsize'])
    plt.suptitle(d['title'], 
                 fontsize = 16, 
                 fontweight = 'bold',
                 color = '#A51C30')
    # Histogram
    ax = pl.subplot(gs[0, 0])
    sns.histplot(d['residuals'], bins = 20, kde = True, ax = ax)
    plt.title('Histogram of Residuals', title_font_dict)
    plt.ylabel('Count', axis_font_dict)
    plt.xlabel('Residual Values', axis_font_dict)
    # QQ Plot
    ax = pl.subplot(gs[0, 1])
    ss.probplot(d['residuals'], plot = ax)
    plt.title('Q-Q Normal plot of residuals', title_font_dict)
    plt.ylabel('Ordered Values', axis_font_dict)
    plt.xlabel('Theoretical Quantiles', axis_font_dict)
    # Residuals vs. fitted values
    RMSE = np.std(d['residuals'])
    ax = pl.subplot(gs[1, :])
    sns.scatterplot(x = d['prediction'], y = d['residuals'], ax = ax)
    ax.axhline(0.0, color = 'red', linewidth = 1.0)
    ax.axhline(2.0 * RMSE, color = 'red', linestyle = 'dashed', linewidth = 1.0)
    ax.axhline(-2.0 * RMSE, color = 'red', linestyle = 'dashed', linewidth = 1.0)
    plt.title('Residuals vs. Predicted', title_font_dict)
    plt.ylabel('Residuals', axis_font_dict)
    plt.xlabel('Predicted values', axis_font_dict)
    plt.tight_layout()
    return(gs)

# Function to plot bs coefficients or effects
def plot_bs_coeff_fun(d):
    if 'effects' in d:
        c = d['effects']
        hist_title = 'Histogram of Effects'
        hist_x_label = 'Bootstrap Effect Values'
    elif 'coefficients' in d:
        c = d['coefficients']
        hist_title = 'Histogram of Coefficients'
        hist_x_label = 'Bootstrap Coefficient Values'
    # Mean, lower and upper bounds
    mean = np.mean(c)
    p = 100 * d['alpha'] / 2.0
    uci = np.percentile(c, 100 - p)
    lci = np.percentile(c, p)
    fig, ax = plt.subplots(nrows = 1, ncols = 2, figsize = d['figsize'])
    plt.suptitle(d['title'], 
                 fontsize = 16, 
                 fontweight = 'bold',
                 color = '#A51C30')
    # Plot a histogram
    ax[0].hist(c, bins = d['bins'])
    ax[0].axvline(mean, color = 'red', linewidth = 1)
    ax[0].axvline(uci, color = 'red', linewidth = 1, linestyle = '--')
    ax[0].axvline(lci, color = 'red', linewidth = 1, linestyle = '--')
    trans = ax[0].get_xaxis_transform()
    for val, label, y in [(mean, 'Mean', 0.95),
                          (uci,  'UCI',  0.85),
                          (lci,  'LCI',  0.85)]:
        ax[0].text(val, y, f"{label}: {val:.4f}",
                   transform = trans,
                   color = 'red', fontsize = 9, fontweight = 'bold',
                   ha = 'center', va = 'top',
                   bbox = dict(facecolor = 'white', edgecolor = 'none', alpha = 0.8, pad = 1))
    ax[0].set_title(hist_title, title_font_dict)
    ax[0].set_xlabel(hist_x_label, axis_font_dict)
    # Plot the Q-Q Normal plot
    ss.probplot(c, plot = ax[1])
    ax[1].set_title('Q-Q Normal Plot', title_font_dict)
    ax[1].set_xlabel('Theoretical Quantiles', axis_font_dict)
    plt.tight_layout()
    return fig

# Function to do a stratified bs
def bs_strat_fun(df, c):
    strats = df[c].drop_duplicates()
    bs_df = pd.DataFrame()
    for s in strats:
        strat_df = df[df[c] == s]
        n_samples = strat_df.shape[0]
        bs_df = pd.concat([bs_df, strat_df.sample(n = n_samples, replace = True)])    
    return bs_df

# Function to plot effects
def plot_effects_fun(d):
    df = d['data'].reset_index(drop = True)
    for i in ['bar_label', 'bar_min', 'bar_height']:
        df = df.rename(columns = {d[i]: i})
    fig, ax = plt.subplots(figsize = d['figsize'])
    ax.set_title( d['title'], fontdict = title_large_font_dict)
    df.plot(kind = 'bar',
            y = 'bar_height',
            x = d['x'],
            bottom = df['bar_min'],
            color = df['color'],
            legend = False,
            alpha = 0.5,
            ax = ax)
    for i, row in df.iterrows():
        ax.hlines(row['bar_label'], i - 0.25, i + 0.25, color = 'black', lw = 2, zorder = 3)
        ax.annotate(f"{row['bar_label']:.1%}",
                    xy = (i, row['bar_label']),
                    xytext = (0, 6),
                    textcoords = 'offset points',
                    ha = 'center', 
                    va = 'bottom',
                    fontweight = 'bold')
    ax.set_ylabel(d['y_label'], fontdict = axis_font_dict)
    ax.set_xlabel(d['x_label'], fontdict = axis_font_dict)
    ax.yaxis.set_major_formatter('{x:,.0%}')
    ax.axhline(0, color = 'black')
    plt.grid(axis = 'y')
    plt.tight_layout()
    return fig

# Function to include missing 0s in a df
def zero_in_df_fun(df, y):
    xs = [c for c in df.columns if c != y]
    zero_df = df[[xs[0]]].drop_duplicates().reset_index(drop = True)
    for i in range(1, len(xs)):
        zero_df = zero_df.merge(df[[xs[i]]].drop_duplicates(), how = 'cross').reset_index(drop = True)
    zero_df = zero_df.merge(df, on = xs, how = 'left')
    zero_df[y] = zero_df[y].fillna(0).astype(df[y].dtype)
    return zero_df

# Function to plot posterior distribution
def station_post_dist_fun(d):
    fig, ax = plt.subplots(figsize = d['figsize'])
    ax.set_title(d['title'], fontdict = title_large_font_dict)
    min_x = d['thetas'][len(d['thetas']) - 1]
    max_x = 0
    for index, row in d['data'].iterrows():
        post_pdf = ss.beta.pdf(d['thetas'], d['prior_a'] + row['success'], d['prior_b'] + row['failure'])
        post_pdf = post_pdf / sum(post_pdf)
        min_x = min(min_x, d['thetas'][next((i for i, x in enumerate(post_pdf) if x > 0.000001), None)])
        max_x = max(max_x, d['thetas'][next((i for i in reversed(range(len(post_pdf))) if post_pdf[i] > 0.000001), -1)])
        plt.plot(d['thetas'], post_pdf, label = row['bike_year'], color = row['color'])
        plt.fill_between(thetas, post_pdf, color = row['color'], alpha = 0.25)
        # label
        max_idx = np.argmax(post_pdf)
        max_theta = thetas[max_idx]
        max_val = post_pdf[max_idx]
        plt.annotate(f'{max_theta:.1%}',
                     xy = (max_theta, max_val),
                     xytext = (0, 0),
                     textcoords = 'offset points',
                     ha = 'center', va = 'bottom',
                     fontsize = 9, color = row['color'])
    ax.set_ylabel('Probability Density', fontdict = axis_font_dict)
    ax.set_xlabel(r'$\theta$', fontdict = axis_font_dict)
    ax.xaxis.set_major_formatter('{x:,.0%}')
    plt.xlim(min_x, max_x)
    plt.grid(axis = 'y')
    plt.legend(loc = 'upper right')
    return fig

# Functions to retrieve coefficients or calculate effect from model
def model_coeff_fun(model, log = False):
    df = pd.DataFrame(model.summary().tables[1])
    df.columns = ['coef_name' if c.data == '' else c.data for c in df.iloc[0]]
    df = df[1:].reset_index(drop = True)
    # Reformat columns
    for c in df.columns:
        df[c] = [c.data for c in df[c]]
    for c in ['coef', '[0.025', '0.975]']:
        df[c] = [float(c) for c in df[c]]        
    # Add Significance
    p_name = [c for c in df.columns if 'P>|' in c][0]
    df = df.rename(columns = {p_name: 'p_value',
                              '[0.025': 'coef_025',
                              '0.975]': 'coef_975'})
    df['sign'] = [float(c) < 0.05 for c in df['p_value']]
    # Split and clean up interaction
    contains_inter = sum(df['coef_name'].str.contains(':')) > 0
    if contains_inter:    
        df[['coef_name', 'inter_name']] = df['coef_name'].str.split(':', expand = True).fillna('None')
        df[['inter_name', 'inter_var']] = df['inter_name'].str.split('[', expand = True).fillna('None')
        df[['inter_name', 'inter_ref']] = df['inter_name'].str.split(',', expand = True).fillna('None')
        df['inter_name'] = [i.replace('C(', '') for i in df['inter_name']] 
        df['inter_var'] = [i.replace('T.', '').replace(']', '') for i in df['inter_var']]
        df['inter_ref'] = [i.replace('Treatment(reference=', '').replace('))', '').replace("'", '') for i in df['inter_ref']]
    # Split and clean up coefficient name
    df[['coef_name', 'coef_var']] = df['coef_name'].str.split('[', expand = True).fillna('None')
    df[['coef_name', 'coef_ref']] = df['coef_name'].str.split(',', expand = True).fillna('None')
    df['coef_name'] = [i.replace('C(', '').replace(')', '') for i in df['coef_name']]
    # Clean up coefficient predictor and reference
    df['coef_var'] = [i.replace('T.', '').replace(']', '') for i in df['coef_var']]
    df['coef_ref'] = [i.replace('Treatment(reference=', '').replace('))', '').replace("'", '') for i in df['coef_ref']]
    # Combine Coeff and Name
    df['coef_name'] = [n if v == 'None' else n + '_' + v for n, v in zip(df['coef_name'], df['coef_var'])]        
    if contains_inter: 
        df['inter_name'] = [n if v == 'None' else n + '_' + v for n, v in zip(df['inter_name'], df['inter_var'])]
        df = df[['coef_name', 'coef_ref', 'inter_name', 'inter_ref', 'p_value', 'sign', 'coef', 'coef_025', 'coef_975']]
    else:
        df = df[['coef_name', 'coef_ref', 'p_value', 'sign', 'coef', 'coef_025', 'coef_975']]
    # Convert to effects if log, otherwise keep coefficients
    if log:
        df.columns = [c.replace('coef', 'effect') for c in df.columns]
        df = df[df['effect_name'].isin(['Intercept', 'alpha']) == False].reset_index(drop = True)
        for c in ['effect', 'effect_025', 'effect_975']:
            df[c] = [np.exp(c) - 1 for c in df[c]]
    return df

# Functions to get marginal effects from GLM
def model_marginal_effect_fun(glm, at = 'mean'):
    df = glm.get_margeff(at = at).summary_frame().reset_index()
    df = df.rename(columns = {'dy/dx': 'marginal_effect',
                              'Pr(>|z|)': 'p_value',
                              'Conf. Int. Low': 'ci_low',
                              'Cont. Int. Hi.': 'ci_hi'})
    # Add Significance
    df['sign'] = [float(c) < 0.05 for c in df['p_value']]
    # Split and clean up interaction
    contains_inter = sum(df['index'].str.contains(':')) > 0
    if contains_inter:    
        df[['coef_name', 'inter_name']] = df['index'].str.split(':', expand = True).fillna('None')
        df[['inter_name', 'inter_var']] = df['inter_name'].str.split('[', expand = True).fillna('None')
        df[['inter_name', 'inter_ref']] = df['inter_name'].str.split(',', expand = True).fillna('None')
        df['inter_name'] = [i.replace('C(', '') for i in df['inter_name']] 
        df['inter_var'] = [i.replace('T.', '').replace(']', '') for i in df['inter_var']]
        df['inter_ref'] = [i.replace('Treatment(reference=', '').replace('))', '').replace("'", '') for i in df['inter_ref']]
    # Split and clean up coefficient name
    df[['coef_name', 'coef_var']] = df['index'].str.split('[', expand = True).fillna('None')
    df[['coef_name', 'coef_ref']] = df['coef_name'].str.split(',', expand = True).fillna('None')
    df['coef_name'] = [i.replace('C(', '').replace(')', '') for i in df['coef_name']]
    # Clean up coefficient predictor and reference
    df['coef_var'] = [i.replace('T.', '').replace(']', '') for i in df['coef_var']]
    df['coef_ref'] = [i.replace('Treatment(reference=', '').replace('))', '').replace("'", '') for i in df['coef_ref']]
    # Combine Coeff and Name
    df['coef_name'] = [n if v == 'None' else n + '_' + v for n, v in zip(df['coef_name'], df['coef_var'])]        
    if contains_inter: 
        df['inter_name'] = [n if v == 'None' else n + '_' + v for n, v in zip(df['inter_name'], df['inter_var'])]
        df = df[['coef_name', 'coef_ref', 'inter_name', 'inter_ref', 'p_value', 'sign', 'marginal_effect', 'ci_low', 'ci_hi']]
    else:
        df = df[['coef_name', 'coef_ref', 'p_value', 'sign', 'marginal_effect', 'ci_low', 'ci_hi']]
    return df

# Scatter plot of combined effects
def plot_dist_dur_fun(d):
    df = d['data'].reset_index(drop = True)
    df = df[df['effect_name'].str.contains(d['effect'])]
    df['effect_name'] = df['effect_name'].str.replace(d['effect'] + '_', '')
    # Scatter Plot
    fig, ax = plt.subplots(figsize = d['figsize'])
    ax.set_title( d['title'], fontdict = title_large_font_dict)
    sns.scatterplot(x = df['duration'], y = df['distance'], ax = ax)
    # 4 Quadrants
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    ax.fill_between([0, xmax], 0, ymax, color ='tab:green', alpha = 0.12, zorder = 0)
    ax.fill_between([xmin, 0], 0, ymax, color = 'tab:blue', alpha = 0.12, zorder = 0)
    ax.fill_between([xmin, 0], ymin, 0, color = 'tab:red', alpha = 0.12, zorder = 0)
    ax.fill_between([0, xmax], ymin, 0, color = 'tab:orange', alpha = 0.12, zorder = 0) 
    ax.axvline(0, color = 'black', linestyle = '--', linewidth = 1)
    ax.axhline(0, color = 'black', linestyle = '--', linewidth = 1)
    ax.text(0.99, 0.99, 'Take longer, go farther', transform = ax.transAxes, ha = 'right', va = 'top', fontsize = 10, fontweight = 'bold')
    ax.text(0.01, 0.99, 'Go farther, quicker', transform = ax.transAxes, ha = 'left', va = 'top', fontsize = 10, fontweight = 'bold')
    ax.text(0.99, 0.01, 'Lingering in the vicinity ', transform = ax.transAxes, ha = 'right', va = 'bottom', fontsize = 10, fontweight = 'bold')
    ax.text(0.01, 0.01, 'Quick and stay closer', transform = ax.transAxes, ha = 'left', va = 'bottom', fontsize = 10, fontweight = 'bold')
    # Labels 
    for _, row in df.iterrows():
        ax.annotate(row['effect_name'],
                    (row['duration'], row['distance']),
                    xytext = (5, 5),
                    textcoords = 'offset points',
                    fontsize = 9)
    # Connect
    if 'connect_plot' in d:
        connect_df = df[df['effect_name'].isin(d['connect_plot'])]
        ax.plot(connect_df['duration'], connect_df['distance'], color = 'red', linestyle = '--', linewidth = 1, zorder = 2)    
    # Finalize
    ax.set_ylabel(d['y_label'], fontdict = axis_font_dict)
    ax.set_xlabel(d['x_label'], fontdict = axis_font_dict)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.yaxis.set_major_formatter('{x:,.0%}')
    ax.xaxis.set_major_formatter('{x:,.0%}')
    return fig

# Prior Predictive Plot
def plot_prior_pred_fun(d):
    pc = azp.plot_dist(d['prior_checks'],
                       group = 'prior',
                       var_names = d['var_names'],
                       figure_kwargs = {'figsize': d['figsize'],
                                        'layout': 'constrained'})
    plt.gcf().suptitle(d['title'],
                       fontsize = 16,
                       fontweight = 'bold',
                       color = '#A51C30')
    for ax in plt.gcf().axes:
        for line in ax.get_lines():
            x, y = line.get_xdata(), line.get_ydata()
            if len(x) > 50: 
                ax.fill_between(x, y, color = 'grey', alpha = 0.5)
        ax.axvline(0, color = 'red', ls = ':', lw = 1)
    return plt.gcf()

# Function for Density and Trace Plots
def plot_trace_fun(d):
    axes = az.plot_trace(d['idata'],
                         var_names = d['var_names'],
                         compact = False,
                         figsize = d['figsize'])
    labels = d['labels']
    for row, name in zip(axes, labels):
        row[0].set_title(labels[name], title_font_dict)
        row[1].set_title('')
        row[0].set_ylabel('Density', axis_font_dict)
        row[1].set_ylabel('Log-odds', axis_font_dict)
        axes[-1, 0].set_xlabel('Log-odds', axis_font_dict)
        axes[-1, 1].set_xlabel('Iteration', axis_font_dict)
    fig = plt.gcf()
    fig.suptitle(d['title'],
                 fontsize = 16,
                 fontweight = 'bold', 
                 color = '#A51C30')
    fig.tight_layout()
    return plt.gcf()

# Function Plot Highest Density Intervals
def plot_hdi_fun(d):
    axes = az.plot_forest(d['idata'],
                          var_names = d['var_names'],
                          hdi_prob = d['hdi_prob'],
                          figsize = d['figsize'])
    ax = axes[0]
    ax.axvline(0, color = 'grey', ls = ':', lw = 1)
    ax.set_title('')
    ax.set_xlabel('Log-odds', axis_font_dict)
    ax.set_yticklabels(d['labels'][::-1])
    fig = plt.gcf()
    fig.suptitle(d['title'] + ' - ' + format(d['hdi_prob'], '.0%') + ' highest density intervals',
                 fontsize = 16,
                 fontweight = 'bold',
                 color = '#A51C30')
    fig.tight_layout()
    return plt.gcf()

# Function to plot posterior distribution
def plot_post_dist_fun(d):
    pc = azp.plot_dist(d['idata'],
                       var_names = d['var_names'],
                       kind = 'kde',
                       backend = 'matplotlib',
                       visuals = {'dist': {'color': 'blue', 'linewidth': 2},
                                  'credible_interval': {'color': 'black'},
                                  'point_estimate': {'color': 'red'},
                                  'point_estimate_text': {'color': 'black'}},
                       figure_kwargs = {'figsize': d['figsize'], 
                                        'layout': 'constrained'})
    titles = d['titles']
    colors = d['colors']
    fig = plt.gcf()
    for ax, t, c in zip(fig.axes, titles, colors):
        for line in ax.get_lines():
            x, y = line.get_xdata(), line.get_ydata()
            if len(x) > 50: 
                ax.plot(x, y, color = c, linewidth = 2, label = t)
                ax.fill_between(x, y, color = c, alpha = 0.25)
        ax.axvline(0, color = 'grey', ls = ':', lw = 1)
        ax.set_title(t)
        ax.set_xlabel('Log-odds', axis_font_dict)
        fig.suptitle(d['title'],
                     fontsize = 16,
                     fontweight = 'bold',
                     color = '#A51C30')
    return plt.gcf()

# Function to plot MCSE and ESS
def render_fun(plot_fn):
    plot_fn()
    buf = io.BytesIO()
    # pad_inches=0.02 crops the whitespace around each plot
    plt.gcf().savefig(buf, format="png", dpi=200, bbox_inches="tight", pad_inches=0.02)
    plt.close("all")
    buf.seek(0)
    return plt.imread(buf)

def plot_mcse_ess_fun(d):
    imgs = [render_fun(lambda: azp.plot_mcse(d['idata'])),
            render_fun(lambda: azp.plot_ess(d['idata'], kind = 'local')),
            render_fun(lambda: azp.plot_ess(d['idata'], kind = 'quantile'))]
    titles = ['Monte Carlo standard error by quantile',
              'Local effective sample size',
              'Quantile effective sample size']
    # Plot
    fig, axes = plt.subplots(3, 1,
                             figsize = d['figsize'],
                             constrained_layout = True)
    # Format
    for ax, im, t in zip(axes, imgs, titles):
        ax.imshow(im)
        ax.axis('off')
        ax.set_title(t, axis_font_dict)
        fig.suptitle(d['title'],
                     fontsize = 16,
                     fontweight = 'bold',
                     color = '#A51C30')
    plt.show()
    return 

# Function to plot calibration plot built with the PAVA
def plot_ppc_pava_fun(d):
    pc = azp.plot_ppc_pava(d['idata'],
                           data_type = 'binary',
                           figure_kwargs = {'figsize': d['figsize'],
                                            'layout': 'constrained'})
    fig = plt.gcf()
    ax = fig.axes[0]
    ax.set_title(d['response'], title_font_dict)
    ax.set_xlabel('Predicted Probability of ' + d['response'], axis_font_dict)
    ax.set_ylabel('Conditional Event Probability', axis_font_dict)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1%}'))
    fig.suptitle(d['title'],
                 fontsize = 16,
                 fontweight = 'bold',
                 color = '#A51C30')
    return plt.gcf()

# Funtion to plot a posterior predictive check
def plot_posterior_pred_fun(d):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        pc = azp.plot_ppc_tstat(d['idata'],
                                t_stat = 'mean',
                                figure_kwargs = {'figsize': d['figsize'],
                                                 'layout': 'constrained'})
    # Observed mean line, styled to match
    y_mean_ds = xr.Dataset({d['response']: idata.observed_data[d['response']].mean()})
    pc.map(azp.visuals.vline,
           'vline_obs_mean',
            data = y_mean_ds,
            color = '#A51C30',
            linestyle = '--')
    # Plot
    fig = plt.gcf()
    ax = fig.axes[0]
    ax.set_title(d['response'] + ' (mean)', title_font_dict)
    ax.set_xlabel(d['response'], axis_font_dict)
    ax.set_ylabel('')
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1%}'))
    fig.suptitle(d['title'],
                 fontsize = 16,
                 fontweight = 'bold',
                 color = '#A51C30')
    return plt.gcf()

# Posterior CI
def post_ci_fun(x, conf, f):
    mean = x.mean()
    percentile_lb = ((1 - conf) / 2) * 100
    percentile_ub = 100 - percentile_lb
    ci_lb, ci_ub = np.percentile(x, [percentile_lb, percentile_ub])
    string = format(mean, f)  + ' (' + format(conf, '.0%') + ' CI: ' + format(ci_lb, f)\
        + ' to ' + format(ci_ub, f) + ')'
    return string
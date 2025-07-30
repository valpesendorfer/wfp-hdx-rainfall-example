import marimo

__generated_with = "0.14.11"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        r"""
    # Yemen: 3-month rainfall anomaly

    To celebrate the occasion of the release of [updated WFP rainfall datsets on the Humanitarian Data exchange (HDX)](https://www.linkedin.com/posts/ocha-centre-for-humanitarian-data_new-data-update-world-food-programme-chirps-activity-7353329221580075008-rTtA?utm_source=share&utm_medium=member_desktop&rcm=ACoAACAIWhgBe6stzzBvibABmUgXzO5_mrOpTxw), I thought I'd create a quick notebook to showcase how to directly access the [WFP datasets](https://data.humdata.org/dataset/?dataseries_name=WFP+-+Rainfall+Indicators+at+Subnational+Level), and how to quickly create simple analysis and visualizations.

    As showcase I've chosen the most popular WFP rainfall datasets on the platform: [Yemen: Rainfall Indicators at Subnational Level](https://data.humdata.org/dataset/yem-rainfall-subnational).
    """
    )
    return


@app.cell
def _():
    # imports
    import marimo as mo
    import duckdb
    import geopandas as gpd
    import pandas as pd
    import altair as alt

    from hdx.api.configuration import Configuration
    from hdx.data.dataset import Dataset
    return Configuration, Dataset, alt, duckdb, gpd, mo, pd


@app.cell
def _(Configuration):
    # authenticate with HDX
    _ = Configuration.create(Configuration(user_agent="hdx-test", hdx_site="prod", hdx_read_only=True))


    return


@app.cell
def _(duckdb):
    # create duckdb connection and load required modules
    con = duckdb.connect()
    _ = con.execute("""
    INSTALL SPATIAL; LOAD SPATIAL;
    INSTALL HTTPFS; LOAD HTTPFS;
    """)
    return (con,)


@app.cell
def _(Dataset, gpd, pd):
    # define helper functions
    def get_dataset_urls(hdx_dataset_name: str) -> pd.DataFrame:
        """Returns name and URL for HDX dataset resources"""
        ds = Dataset.read_from_hdx(hdx_dataset_name)
        return pd.DataFrame([(x["name"],x["download_url"]) for x in ds.resources], columns=["name", "url"])


    def df_to_gdf(x: pd.DataFrame, crs="epsg:4326", geom="geometry") -> gpd.GeoDataFrame:
        """Converts pandas dataframe to geodataframe"""
        x = gpd.GeoDataFrame(x)
        x[geom] = gpd.GeoSeries.from_wkt(x[geom])
        x.set_geometry(geom, crs=crs, inplace=True)
        return x
    return df_to_gdf, get_dataset_urls


@app.cell
def _(mo):
    mo.md(r"""First, let's access the dataset metadata from HDX and see which resources we have available:""")
    return


@app.cell
def _(get_dataset_urls):
    res = get_dataset_urls("yem-rainfall-subnational")
    res
    return (res,)


@app.cell
def _(mo):
    mo.md(
        r"""
    The WFP datasets contain 2 resources:

    - one containing the full timeseries back to 1981
    - one containing the last 5 years to date

    We'll use the resource with the last 5 years, which is definitely smaller in size and will contain all the data we need for this simple analysis.
    """
    )
    return


@app.cell
def _(res):
    url, = res[res.name.str.endswith("5ytd.csv")].url.values
    return (url,)


@app.cell
def _(mo):
    mo.md(
        r"""
    ---
    To actually load the data from the URL, we'll use one of my favourite recent tools - [duckdb](https://duckdb.org/). It can directly load the data into a database table, and it only requires one line of SQL!

    Let's have a look at the first 10 rows of the table to understand how the data looks like:
    """
    )
    return


@app.cell
def _(con, mo, url):
    _df = mo.sql(
        f"""
        CREATE OR REPLACE TABLE rainfall as (SELECT * FROM read_csv('{url}'));
        SELECT * from rainfall limit 10;
        """,
        engine=con
    )
    return (rainfall,)


@app.cell
def _(mo):
    mo.md(
        r"""
    Very nice! I can see there's the `date`, we have `adm_level` indicating if it's administrative level 1 or 2, the OCHA `PCODE` which will be relevant in just a bit, and then all the rainfall indicators as described in the [dataset's description](https://data.humdata.org/dataset/yem-rainfall-subnational).

    For this example, we'll focus on the 3-month rainfall anomaly `r3q`, which tells us how the aggregated rainfall over the three months prior the selected timestamp stack up against the long term average (`r3h_avg`), which is calculated over the reference period 1989 - 2018.
    """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    To be able to show some nice visualizations, we're missing only one last thing: the subnational boundaries for Yemen! These are also alvailable as [dataset on HDX](https://data.humdata.org/dataset/cod-ab-yem), so we can access them directly as well!

    Let's have a look at the available resources of the dataset:
    """
    )
    return


@app.cell
def _(get_dataset_urls):
    cod_res = get_dataset_urls("cod-ab-yem")
    cod_res
    return (cod_res,)


@app.cell
def _(mo):
    mo.md(
        r"""
    Great! It's all there. The boundaries of the different levels are zipped up in either geopackage or topojson - I'll go ahead and use geopackage. To proceed I do need to cheat just a tiny little bit 😄 - the geopackage contains all layers for all admin levels. I only need levels 1 and 2, but there's no way to programmatically determine how these layers are called. So I did download them (so you don't have to) and had a look:

    - admin1: `yem_admbnda_adm1_govyem_cso`
    - admin2: `yem_admbnda_adm2_govyem_cso`
    """
    )
    return


@app.cell
def _(cod_res):
    # get url and name for geopackage
    cod_url, = cod_res[cod_res.name.str.endswith("GPKG.zip")].url.values
    cod_name, = cod_res[cod_res.name.str.endswith("GPKG.zip")].name.values
    return cod_name, cod_url


@app.cell
def _(mo):
    mo.md(
        r"""
    Now that we know the layer names we are ready to go! And we'll use another favourite trick of mine - the [GDAL Virtual File Systems](https://gdal.org/en/stable/user/virtual_file_systems.html).

    I'll still be using `duckdb` to handle the boundary files (which by the way as a [kickass spatial extension](https://duckdb.org/docs/stable/core_extensions/spatial/overview.html)), but the underlying library which is handling the geospatial data is ultimately using GDAL as well, which means we can use this trick and it'll work! 

    Basically we're adding two prefixes to the URL: `/vsizip/` and `/vsicurl/` which combines to `/vsizip//vsicurl` followed by the actual URL. This tells gdal that it should expect a compressed zipfile, and that the zipfile is located on an external server so it needs to download it into memory. Finally, we also need to specify the layer to make sure we're getting the right data 😁

    So for example for admin level 1, the original URL with the format `https://data.humdata.org/...yem_adm_govyem_cso_ochayemen_20191002_gpkg.zip` becomes `/vsizip//vsicurl/https://data.humdata.org/...yem_adm_govyem_cso_ochayemen_20191002_gpkg.zip` and we'll pass in the `layer=` keyword argument to the duckdb spatial function `st_read` to select the layer we need.

    The awesome part here is that we're only acccessing the data we need! We don't have to download the full zipfile and then load, we're loading the required bits right away and leave the rest be - magic 🪄
    """
    )
    return


@app.cell
def _(cod_name, cod_url, con, mo):
    _df = mo.sql(
        f"""

            CREATE OR REPLACE TABLE adm_1 AS SELECT * from st_read("/vsizip//vsicurl/{cod_url}/{cod_name.replace('zip', 'gpkg')}", layer="yem_admbnda_adm1_govyem_cso");

            CREATE OR REPLACE TABLE adm_2 AS SELECT * from st_read("/vsizip//vsicurl/{cod_url}/{cod_name.replace('zip', 'gpkg')}", layer="yem_admbnda_adm2_govyem_cso");

        """,
        engine=con
    )
    return adm_1, adm_2


@app.cell
def _(mo):
    mo.md(
        r"""
    ---
    Now let's look at which dates are availble in the dataset. We can combine the query with the data version, which shows that the most recent timestamp is a `forecast`, followed by two "preliminary" observations and the rest "final" observations:
    """
    )
    return


@app.cell
def _(con, mo, rainfall):
    date_ver = mo.sql(
        f"""
        SELECT DISTINCT(date)::VARCHAR || ': ' || version as date_ver from rainfall where adm_level = 1 ORDER by date DESC;
        """,
        engine=con
    )
    return (date_ver,)


@app.cell
def _(mo):
    mo.md(r"""I'll select the last preliminary version, as for this quick analysis I'm not interested in a forecast.""")
    return


@app.cell
def _(date_ver, mo):
    # With search functionality
    date_ver_dropdown = mo.ui.dropdown(
        options=[x[0] for x in date_ver.values],
        value="2025-07-11: prelim",
        label="Select date: ",
        searchable=True,
    )
    date_ver_dropdown
    return (date_ver_dropdown,)


@app.cell
def _(mo):
    mo.md(r"""Great, let's combine everything - our selected timestamp, the 3-month rainfall anomaly at the Governorate level (admin-1) and the boundaries to create a geodataframe which is ready for visualization:""")
    return


@app.cell
def _(adm_1, con, date_ver_dropdown, mo, rainfall):
    adm_1_rf = mo.sql(
        f"""
        WITH
            adm AS (
                SELECT
                    admin1Name_en,
                    admin1Pcode as PCODE,
                    st_astext (shape) AS geometry
                FROM
                    adm_1
            ),
            rf as (
                SELECT
                    date,
                    r3q,
                    PCODE
                FROM
                    rainfall
                WHERE
                    adm_level = 1
                    and date = '{date_ver_dropdown.value.split(":")[0]}'
            )
        SELECT
            *
        from
            rf
            JOIN adm ON rf.PCODE = adm.PCODE;
        """,
        engine=con
    )
    return (adm_1_rf,)


@app.cell
def _(mo):
    mo.md(r"""Awesome, this let's us create this quick map of the rainfall anomaly in Yemen for each Governorate! The colors range from yellow to red, looking at the legend this indicates a below average aggregated rainfall during the last three months.""")
    return


@app.cell
def _(adm_1_rf, df_to_gdf):
    _m = df_to_gdf(adm_1_rf).explore(
        column="r3q",
        cmap="RdYlBu",
        vmin=50,
        vmax=130,
        center=100,
        legend=True,
        legend_kwds={"caption": "3-monthly Rainfall Anomaly (% of normal)", "shrink": 0.1},
        tooltip=["admin1Name_en", "r3q"],
        popup=True
    )
    _m
    return


@app.cell
def _(mo):
    mo.md(r"""Let's select a Governorate in the west, which has a negative value but where we also expect some agriculture to be present:""")
    return


@app.cell
def _(con, mo):
    # With search functionality
    adm1_dropdown = mo.ui.dropdown(
        options=[
            x[1] + ": " + x[0]
            for x in con.sql(
                "SELECT admin1Name_en, admin1PCODE from adm_1;"
            ).fetchall()
        ],
        value="YE18: Al Hodeidah",
        label="Select Admin 1: ",
        searchable=True,
    )
    adm1_dropdown
    return (adm1_dropdown,)


@app.cell
def _(mo):
    mo.md(r"""This gives us a dataframe just like the one above we had for Governorates, but this time zoomed in at District level (admin-2):""")
    return


@app.cell
def _(adm1_dropdown, adm_2, con, date_ver_dropdown, mo, rainfall):
    adm_2_rf = mo.sql(
        f"""
        WITH
            adm AS (
                SELECT
                    admin2Name_en,
                    admin2Pcode as PCODE,
                    st_astext (shape) AS geometry
                FROM
                    adm_2
                where
                    admin1Pcode = '{adm1_dropdown.value.split(":")[0]}'
            ),
            rf as (
                SELECT
                    date,
                    r3q,
                    PCODE
                FROM
                    rainfall
                WHERE
                    adm_level = 2
                    and date = '{date_ver_dropdown.value.split(":")[0]}'
            )
        SELECT
            *
        from
            rf
            JOIN adm ON rf.PCODE = adm.PCODE;
        """,
        engine=con
    )
    return (adm_2_rf,)


@app.cell
def _(mo):
    mo.md(r"""And again, we're plotting a quick web map to get an overview. The yellow and red colors are again prevalent, indicating lower rainfall values than usual. I can actually hover over the individual polygons to look at the numerical values of the rainfall anomaly.""")
    return


@app.cell
def _(adm_2_rf, df_to_gdf):
    _m = df_to_gdf(adm_2_rf).explore(
        column="r3q",
        cmap="RdYlBu",
        vmin=50,
        vmax=130,
        center=100,
        legend=True,
        legend_kwds={"caption": "3-monthly Rainfall Anomaly (% of normal)", "shrink": 0.1},
        tooltip=["admin2Name_en", "PCODE", "r3q"],
        popup=True
    )

    _m
    return


@app.cell
def _(mo):
    mo.md(r"""Ok, let's select one of the Districts with a lower anomaly to do a bit of a "deep dive":""")
    return


@app.cell
def _(con, mo):

    adm2_dropdown = mo.ui.dropdown(
        options=[
            x[1] + ": " + x[0]
            for x in con.sql(
                "SELECT admin2Name_en, admin2PCODE from adm_2 ORDER BY admin2Name_en;"
            ).fetchall()
        ],
        value="YE1604: Az Zahir",
        label="Select Admin 2: ",
        searchable=True,
    )
    adm2_dropdown
    return (adm2_dropdown,)


@app.cell
def _(mo):
    mo.md(r"""Again, we get a dataframe - but this time we don't need any polygons or geospatial data. Instead we're looking at the full dataset for this District, showing the last 5 years to date:""")
    return


@app.cell
def _(adm2_dropdown, con, mo, rainfall):
    _df = mo.sql(
        f"""
        SELECT date, r3h as rfh, r3h_avg as rfh_avg from rainfall where PCODE = '{adm2_dropdown.value.split(":")[0]}'
        """,
        engine=con
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    Awesome, this is exactly what we need to produce this nice bar chart below:

    We can see the actual 3-month aggregated rainfall over the full 5 years, plotted in dark blue, and the corresponding long term average in light blue behind. Wherever we have the light blue bars peeking out, we would expect lower anomalies - i.e. the average rainfall was higher than the actual one.

    ---

    To look into detail at the most recent timesteps we visualized above, we can use the slider blelow to select a subset of the dates in the full plot, and we should see a "zoomed in" plot below which shows only the selected timeframe:
    """
    )
    return


@app.cell
def _(adm2_dropdown, alt, con, mo):
    # chart title
    _title = alt.TitleParams(f'Rainfall {adm2_dropdown.value.split(": ")[-1]}', anchor='middle')

    # Background bar: rfh_avg (light blue)
    df = con.sql(f"SELECT date, round(r3h, 2) as rfh, round(r3h_avg, 2) as rfh_avg from rainfall where PCODE = '{adm2_dropdown.value.split(':')[0]}'").df()

    # Brush selection (for the slider)
    brush = alt.selection_interval(encodings=['x'])

    avg_bars = alt.Chart(df, title=_title).mark_bar(
        color='#93F1DF',
        opacity=0.7
    ).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('rfh_avg:Q', title='Rainfall [mm]'),
    )
    # avg_bars

    # Foreground bar: rfh (darker blue)
    rfh_bars = alt.Chart(df).mark_bar(
        color='#225585'
    ).encode(
        x='date:T',
        y='rfh:Q'
    )
    # rfh_bars
    # # Overlay them
    chart = mo.ui.altair_chart((avg_bars + rfh_bars).add_params(brush), chart_selection=False, legend_selection=False)

    return chart, df


@app.cell
def _(alt, df, mo, r):
    df_sub = df.iloc[r.value[0]:r.value[1], :]
    avg_bars_sub = alt.Chart(df_sub).mark_bar(
        color='#93F1DF',
        opacity=0.7
    ).encode(
        x=alt.X('date:T', title='Date'),
        y=alt.Y('rfh_avg:Q', title='Rainfal [mm]'),
    )
    # avg_bars

    # Foreground bar: rfh (darker blue)
    rfh_bars_sub = alt.Chart(df_sub).mark_bar(
        color='#225585'
    ).encode(
        x='date:T',
        y='rfh:Q'
    )
    # rfh_bars
    # # Overlay them
    chart_sub = mo.ui.altair_chart((avg_bars_sub + rfh_bars_sub),chart_selection=False, legend_selection=False)

    return (chart_sub,)


@app.cell
def _(df, mo, pd):

    dts = pd.DatetimeIndex(df["date"]).strftime("%Y-%m-%d")
    r = mo.ui.range_slider(start=0, stop=len(dts)-1, full_width=True, label="Select date range: ", value=[145, 164])
    r
    return dts, r


@app.cell
def _(dts, mo, r):
    with mo.redirect_stdout():
        print(" ".join([dts[r.value[0]], "to", dts[r.value[1]]]))
    return


@app.cell
def _(chart, chart_sub, mo):
    mo.vstack([chart, chart_sub])
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    Having a look at the detail, we can see that there's only a minimal increase in the aggregated rainfall values compared to the long term average staring March, which is in line with the low anomaly values we've seen above.  

    We could spend hours digging into this dataset, and creating different maps and plots 😄 - but this was just meant to be a quick example how to access and start wrangling this data. I hope it's helpful!
    """
    )
    return


if __name__ == "__main__":
    app.run()

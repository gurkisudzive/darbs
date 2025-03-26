from flask import Flask, render_template, request
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import pandas as pd
import glob
from peewee import *

db = SqliteDatabase('world_population.db')


class BaseModel(Model):
    class Meta:
        database = db


class PopulationData(BaseModel):
    country = CharField()
    year = IntegerField()
    population = IntegerField()
    male_percentage = FloatField()
    female_percentage = FloatField()


db.connect()
db.create_tables([PopulationData], safe=True)


def clear_old_charts():
    files = glob.glob('static/*.png')
    for f in files:
        os.remove(f)


def load_data_from_csv():

    df = pd.read_csv("C:\\Users\\elzab\\Desktop\\world_population(1).csv")
    for _, row in df.iterrows():
        PopulationData.create(
            country=row['Country'],
            year=row['Year'],
            population=row['Population'],
            male_percentage=row['Male_Percentage'],
            female_percentage=row['Female_Percentage']
        )


load_data_from_csv()

app = Flask(__name__)


@app.route('/')
def index():
    countries = PopulationData.select(PopulationData.country).distinct()
    return render_template('index.html', countries=countries)


@app.route('/visualize', methods=['POST'])
def visualize():
    clear_old_charts()

    country = request.form.get('country')
    data = PopulationData.select().where(PopulationData.country == country)
    yearly_data = data.order_by(PopulationData.year)

    years = [d.year for d in yearly_data]
    populations = [d.population for d in yearly_data]

    #Populācijas pieauguma diagramma
    from matplotlib.ticker import FuncFormatter
    plt.figure(figsize=(10, 5))
    plt.plot(years, populations, marker='o', linestyle='-')
    plt.xlabel('Year')
    plt.ylabel('Population (miljoniem)')
    plt.title(f'Population Growth in {country}')
    plt.grid()

    def miljoni_formatter(x, pos):
        return f'{x * 1e-6:.1f}M'

    plt.gca().yaxis.set_major_formatter(FuncFormatter(miljoni_formatter))

    # Uzstāda Y ass robežas ar nelielu rezervi
    min_pop = min(populations)
    max_pop = max(populations)
    plt.ylim(min_pop * 0.95, max_pop * 1.05)

    plt.tight_layout()
    plt.savefig('static/population_growth.png')
    plt.close()

    #Sektora diagramma
    country_data = (PopulationData
                    .select(PopulationData.country, fn.SUM(PopulationData.population).alias('total_population'))
                    .group_by(PopulationData.country)
                    .order_by(fn.SUM(PopulationData.population).desc()))

    all_countries = [d.country for d in country_data]
    pop_totals = [d.total_population for d in country_data]

    # Nosaka TOP 5 valstis
    top_5_countries = all_countries[:5]

    labels = [
        c if (c in top_5_countries or c == country) else ''
        for c in all_countries
    ]

    # Procenti rāda tikai tām, kurām ir nosaukums
    def make_autopct(labels):
        def autopct(pct):
            index = make_autopct.index
            label = labels[index]
            make_autopct.index += 1
            return f'{pct:.1f}%' if label != '' else ''
        make_autopct.index = 0
        return autopct

    plt.figure(figsize=(8, 8))
    plt.pie(pop_totals,
            labels=labels,
            autopct=make_autopct(labels),
            startangle=90,
            textprops={'fontsize': 9},
            labeldistance=1.15)
    plt.title('Population Distribution by Country')
    plt.tight_layout()
    plt.savefig('static/country_pie.png', bbox_inches='tight')
    plt.close()



    return render_template('result.html',
                           country=country,
                           pop_growth='static/population_growth.png',
                           country_pie='static/country_pie.png',
                           gender_dist='static/gender_distribution.png')


if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True)
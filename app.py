from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from dash.dependencies import Input, Output, State, MATCH
from sshtunnel import SSHTunnelForwarder
from dash import Dash, dcc, html
import plotly.express as px
from functools import wraps
import pandas as pd
import psycopg2
import datetime
from calculate_cxo_alignment import calculate_alignment_scores
import uuid
import json
import os

def read_questions_from_json(file_path):
    with open(file_path, mode='r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
    
    questions = []
    for key, value in data.items():
        question = {
            "question": f"Question {key}",
            "options": [item["Decision Statement"] for item in value]
        }
        questions.append(question)   
    return questions

questions = read_questions_from_json('assessment_google_sheet.json')

def get_db_connection():
    conn = psycopg2.connect(
        dbname='letsrise_v1',
        user='letsrise_intern',
        password='letsrise',
        host='localhost'
    )
    return conn
conn = get_db_connection()

query1 = """
SELECT * FROM public.user_info ui
INNER JOIN public.assessment_entries ae ON ui.user_id = ae.user_id
INNER JOIN public.consequence_results cr ON ui.user_id = cr.user_id;
"""
query2 = """
SELECT crd.*, ui.name, b.benchmark_name
FROM public.comparison_result_data crd
INNER JOIN public.user_info ui ON crd.user_id = ui.user_id
INNER JOIN public.benchmark b ON crd.benchmark_id = b.benchmark_id
ORDER BY crd.comparison_id ASC;
"""

cur = conn.cursor()
consequence_df = pd.read_sql(query1, conn)
comparison_df = pd.read_sql(query2, conn)

consequence_df = consequence_df.loc[:, ~consequence_df.columns.duplicated()]
required_columns = ['user_id', 'name', 'email', 'age', 'linkedin_url', 'education_level', 'employment_status', 'entrepreneurial_experience', 'current_startup_stage', 'number_of_startups', 'role_in_entrepreneurship', 'industry_experience', 'number_of_previous_startups', 'location', 'gender', 'startup_name', 'assessment_id', 
                    'customer_centric', 'collaborative', 'agile', 'innovative', 'risk_taking', 'visionary', 'hustler', 'passionate', 'resilient', 'educational', 'analytical', 'frugal', 'legacy', 'digital', 'problem_solver', 
                    'delayed_product_market_fit', 'lack_of_product_market_fit', 'unable_to_complete_fundraise', 'lack_of_growth', 'lack_of_revenue', 'high_turnover_of_talent', 'inefficient_processes', 'time_consuming_client_acquisition', 'low_customer_conversion', 'low_customer_satisfaction', 'low_customer_retention', 'high_cash_burnrate', 'high_team_conflict', 'high_key_man_risk', 'lack_of_partnerships_collaborations', 'lack_of_scalability', 'lack_of_data_integrity', 'lack_of_data_security', 'lack_of_marketing', 'lack_of_motivation', 'lack_of_leadership', 'lack_of_innovation', 'lack_of_clarity', 'too_much_dependency_on_external_factors', 'lack_of_technological_advancements', 'lack_of_unique_value_proposition', 'lack_of_customer_variety', 'lack_of_intellectual_property', 'lacking_solution_quality', 'lack_of_supporters', 'missed_opportunities', 'delayed_revenue']
filtered_df = consequence_df[required_columns]

# Initialize Flask
server = Flask(__name__)
server.secret_key = 'supersecretkey' 

# Initialize Dash
dash_app1 = Dash(__name__, server=server, url_base_pathname='/dash1/')

traits = ['customer_centric', 'collaborative', 'agile', 'innovative', 'risk_taking', 'visionary', 'hustler', 'passionate', 'resilient', 'educational', 'analytical', 'frugal', 'legacy', 'digital', 'problem_solver']
consequences = ['delayed_product_market_fit', 'lack_of_product_market_fit', 'unable_to_complete_fundraise', 'lack_of_growth', 'lack_of_revenue', 'high_turnover_of_talent', 'inefficient_processes', 'time_consuming_client_acquisition', 'low_customer_conversion', 'low_customer_satisfaction', 'low_customer_retention', 'high_cash_burnrate', 'high_team_conflict', 'high_key_man_risk', 'lack_of_partnerships_collaborations', 'lack_of_scalability', 'lack_of_data_integrity', 'lack_of_data_security', 'lack_of_marketing', 'lack_of_motivation', 'lack_of_leadership', 'lack_of_innovation', 'lack_of_clarity', 'too_much_dependency_on_external_factors', 'lack_of_technological_advancements', 'lack_of_unique_value_proposition', 'lack_of_customer_variety', 'lack_of_intellectual_property', 'lacking_solution_quality', 'lack_of_supporters', 'missed_opportunities', 'delayed_revenue']

# Get the list of benchmarks and users for the dropdowns
benchmarks = comparison_df['benchmark_name'].unique()
users = comparison_df[['user_id', 'name']].drop_duplicates().to_dict('records')

# Function to format consequence names
def format_consequence_name(name):
    return name.replace('_', ' ').title()
formatted_consequences = [format_consequence_name(c) for c in consequences]

# Define the layout of the app
dash_app1.layout = html.Div([
    html.H1("Benchmark and Trait Scores Comparison", style={'text-align': 'center', 'color': 'var(--primary-color)', 'font-family': 'var(--font-family)', 'margin-bottom': '20px'}),
    html.Div(id='user-info', style={'text-align': 'center', 'margin': '20px', 'font-family': 'var(--font-family)', 'color': 'var(--text-color)'}),
    html.Div([
        dcc.Dropdown(
            id='benchmark-dropdown',
            options=[{'label': benchmark, 'value': benchmark} for benchmark in benchmarks],
            placeholder="Select a benchmark",
            value='Global',
            style={'width': '40%', 'display': 'inline-block', 'margin-right': '20px', 'font-family': 'var(--font-family)', 'color': 'var(--text-color)', 'margin-bottom': '20px'}
        ),
        dcc.Dropdown(
            id='user-dropdown',
            options=[{'label': user['name'], 'value': user['user_id']} for user in users],
            placeholder="Select a user",
            value='02e6fb77-58f9-4930-9ee3-47740bfe618c',  # Default value for "Shamimuzzaman Chowdhury"
            style={'width': '40%', 'display': 'inline-block', 'font-family': 'var(--font-family)', 'color': 'var(--text-color)', 'margin-bottom': '20px'}
        ),
    ], style={'text-align': 'center', 'margin-bottom': '20px'}),
    dcc.Graph(id='benchmark-graph', style={'margin-bottom': '40px', 'height': '500px'}),
    dcc.Graph(id='trait-scores-graph', style={'margin-bottom': '40px', 'height': '500px'}),
    dcc.Graph(id='consequence-graph', style={'margin-bottom': '40px', 'height': '500px'}),
], style={'background-color': 'var(--background-color)', 'font-family': 'var(--font-family)', 'padding': '20px', 'border': '1px solid var(--border-color)', 'box-shadow': '0 4px 8px var(--shadow-color)'})

@dash_app1.callback(
    Output('user-info', 'children'),
    [Input('user-dropdown', 'value')]
)
def update_user_info(selected_user):
    if not selected_user:
        return "Please select a user to see their information."
    
    # Filter the data for the selected user
    user_data = filtered_df[filtered_df['user_id'] == selected_user]
    
    if user_data.empty:
        return "No user data available."
    
    # User info div
    user_info = html.Div([
        html.H2(user_data['name'].values[0], style={'color': 'var(--primary-color)'}),
        html.P(f"Email: {user_data['email'].values[0]}", style={'color': 'var(--text-color)'}),
        html.P(f"Age: {user_data['age'].values[0]}", style={'color': 'var(--text-color)'}),
        html.P(f"LinkedIn: {user_data['linkedin_url'].values[0]}", style={'color': 'var(--text-color)'})
    ])
    
    return user_info

@dash_app1.callback(
    Output('benchmark-graph', 'figure'),
    [Input('benchmark-dropdown', 'value'), Input('user-dropdown', 'value')]
)
def update_benchmark_graph(selected_benchmark, selected_user):
    if not selected_benchmark or not selected_user:
        return px.bar(title="Please select both a benchmark and a user to see the comparison.")
    
    # Filter the data for the selected benchmark and user
    filtered_data = comparison_df[(comparison_df['benchmark_name'] == selected_benchmark) & (comparison_df['user_id'] == selected_user)]
    
    if filtered_data.empty:
        return px.bar(title="No data available for the selected benchmark and user.")
    
    # Create a vertical bar chart for the traits
    trait_data = filtered_data[traits].melt()
    fig = px.bar(trait_data, x='variable', y='value', title=f'Benchmark Comparison for {selected_benchmark}', 
                 labels={'variable': 'Trait', 'value': 'Score'}, color='variable', 
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(
        xaxis={'categoryorder':'total descending'},
        plot_bgcolor='var(--white-color)',
        paper_bgcolor='var(--background-color)',
        font=dict(family='var(--font-family)', color='var(--text-color)'),
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis_title=None,
        yaxis_title="Score",
        showlegend=False
    )
    
    return fig

@dash_app1.callback(
    Output('trait-scores-graph', 'figure'),
    [Input('user-dropdown', 'value')]
)
def update_trait_scores(selected_user):
    if not selected_user:
        return px.bar(title="Please select a user to see their trait scores.")
    
    # Filter the data for the selected user
    user_data = filtered_df[filtered_df['user_id'] == selected_user]
    
    if user_data.empty:
        return px.bar(title="No trait scores available for the selected user.")
    
    trait_data = user_data[traits].melt()
    
    # Create a horizontal bar chart for the user's trait scores
    fig = px.bar(trait_data, y='variable', x='value', orientation='h', title=f'Trait Scores', 
                 labels={'variable': 'Trait', 'value': 'Score'}, color='variable', 
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        plot_bgcolor='var(--white-color)',
        paper_bgcolor='var(--background-color)',
        font=dict(family='var(--font-family)', color='var(--text-color)'),
        margin=dict(l=150, r=50, t=50, b=50),
        yaxis_title=None,
        xaxis_title="Score",
        showlegend=False
    )
    return fig

@dash_app1.callback(
    Output('consequence-graph', 'figure'),
    [Input('user-dropdown', 'value')]
)
def update_consequence(selected_user):
    if not selected_user:
        return px.bar(title="Please select a user to see their consequences.")
    
    # Filter the data for the selected user
    user_data = filtered_df[filtered_df['user_id'] == selected_user]
    consequence_data = user_data[consequences].melt()
    consequence_data = consequence_data[consequence_data['value'] > 0]
    
    if consequence_data.empty:
        return px.bar(title="No consequences with non-zero values for the selected user.")
    
    # Update the consequence_data variable names
    consequence_data['variable'] = consequence_data['variable'].apply(format_consequence_name)
    
    # Create a horizontal bar chart for the user's consequences
    fig = px.bar(consequence_data, y='variable', x='value', orientation='h', title=f'Consequences', 
                 labels={'variable': 'Consequence', 'value': 'Value'}, color='variable', 
                 color_discrete_sequence=px.colors.qualitative.Set3)
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        plot_bgcolor='var(--white-color)',
        paper_bgcolor='var(--background-color)',
        font=dict(family='var(--font-family)', color='var(--text-color)'),
        margin=dict(l=100, r=50, t=50, b=50),
        yaxis_title=None,
        xaxis_title="Value",
        showlegend=False
    )
    
    return fig

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@server.before_request
def before_request():
    if 'user_id' not in session and request.endpoint in ['dashboard', 'benchmark', 'onboarding', 'quiz', 'matching', 'profile', 'subscription']:
        return redirect(url_for('login'))

@server.after_request
def after_request(response):
    return add_no_cache_headers(response)

@server.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))

@server.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user:
            stored_password = user[4]
            if check_password_hash(stored_password, password):
                session['user_id'] = user[1]
                return redirect(url_for('homepage'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@server.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_id = str(uuid.uuid4())
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            cur.execute("INSERT INTO users (user_id, name, email, password) VALUES (%s, %s, %s, %s)", (user_id, name, email, hashed_password))
            conn.commit()
            flash('You have successfully registered!', 'success')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            conn.rollback()
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')

@server.route('/logout')
def logout():
    session.pop('user_id', None)
    session.clear()
    flash('You have successfully logged out', 'success')
    return redirect(url_for('login'))

@server.route('/homepage')
@login_required
def homepage():
    return render_template('homepage.html')

@server.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@server.route('/benchmark')
@login_required
def benchmark():
    return render_template('benchmark.html')

@server.route('/onboarding', methods=['GET', 'POST'])
@login_required
def onboarding():
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the database
    cur.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    name, email = user
    first_name, last_name = name.split(' ', 1) if ' ' in name else (name, '')

    # Fetch challenges from the database
    cur.execute("SELECT stage, challenge FROM startup_challenges")
    challenges = cur.fetchall()

    # Organize challenges by stage
    challenges_by_stage = {}
    for row in challenges:
        stage, challenge = row
        if stage not in challenges_by_stage:
            challenges_by_stage[stage] = []
        challenges_by_stage[stage].append(challenge)

    if request.method == 'POST':
        # Handle form submission as before
        try:
            first_name = request.form['firstName']
            last_name = request.form['lastName']
            email = request.form['email']
            phone_number = request.form['phoneNumber']
            dob_day = int(request.form['dobDay'])
            dob_month = int(request.form['dobMonth'])
            dob_year = int(request.form['dobYear'])
            dob = datetime.date(dob_year, dob_month, dob_day)
            gender = request.form['gender']
            location = request.form['location']
            education_level = request.form['educationLevel']
            employment_status = request.form.getlist('employmentStatus')
            career_experience = request.form.getlist('careerExperience')
            linkedin_url = request.form['linkedinUrl']
            entrepreneurial_experience = int(request.form['entrepreneurialExperience'])
            previous_startups = int(request.form['previousStartups'])
            current_startups = int(request.form['currentStartups'])
            entrepreneurial_experience_type = request.form.getlist('entrepreneurialExperienceType')
            startup_roles = request.form.getlist('startupRoles')
            startup_stage = request.form['startupStage']
            startup_project_name = request.form['startupProjectName']
            first_challenge = request.form['firstChallenge']
            second_challenge = request.form['secondChallenge']
            third_challenge = request.form['thirdChallenge']

            cur.execute("""
                INSERT INTO onboarding_entries (
                    user_id, first_name, last_name, email, phone_number, dob, gender, location, 
                    education_level, employment_status, career_experience, linkedin_url, 
                    entrepreneurial_experience, previous_startups, current_startups, 
                    entrepreneurial_experience_type, startup_roles, startup_stage, 
                    startup_project_name, first_challenge, second_challenge, third_challenge
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                user_id, first_name, last_name, email, phone_number, dob, gender, location, 
                education_level, employment_status, career_experience, linkedin_url, 
                entrepreneurial_experience, previous_startups, current_startups, 
                entrepreneurial_experience_type, startup_roles, startup_stage, 
                startup_project_name, first_challenge, second_challenge, third_challenge
            ))

            cur.execute("UPDATE users SET onboarding_form_completed = TRUE WHERE user_id = %s", (user_id,))
            conn.commit()

            flash('Form submitted successfully!', 'success')
            return redirect(url_for('homepage'))
        except Exception as e:
            conn.rollback()
            flash(f'Error submitting form: {e}', 'danger')

    return render_template('onboarding.html', first_name=first_name, last_name=last_name, email=email, challenges_by_stage=challenges_by_stage)


@server.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    if request.method == 'POST':
        try:
            user_id = session.get('user_id')
            if not user_id:
                flash('User not logged in', 'danger')
                return redirect(url_for('login'))

            # Capture IP address
            submission_ip = request.remote_addr

            # Capture current date
            submission_date = datetime.date.today()

            # Get form data from JSON
            data = request.get_json()
            answers = data.get('answers', [])

            if not answers:
                return jsonify({"message": "No answers provided."}), 400

            # Insert form data into database
            query = """
            INSERT INTO assessment_entries (
                user_id, submission_ip, last_update_date, {columns}
            ) VALUES (
                %s, %s, %s, {placeholders}
            )
            """.format(
                columns=", ".join([f"question{i+1}" for i in range(len(answers))]),
                placeholders=", ".join(["%s"] * len(answers))
            )

            values = [user_id, submission_ip, submission_date] + answers

            cur.execute(query, values)
            conn.commit()

            # Update user table
            cur.execute("UPDATE users SET quiz_completed = TRUE WHERE user_id = %s", (user_id,))
            conn.commit()

            return jsonify({"message": "Quiz submitted successfully!"})
        except Exception as e:
            conn.rollback()
            print(f"Error submitting form: {e}")
            return jsonify({"message": f"Error submitting form: {e}"}), 500

    questions = read_questions_from_json('assessment_google_sheet.json')
    return render_template('quiz.html', questions=questions)

# Extract and prepare data
query3 = """
SELECT * FROM public.user_info
ORDER BY user_id ASC;
"""

df = pd.read_sql(query3, conn)
df_exploded = df.assign(industry_experience=df['industry_experience'].str.split('\n')).explode('industry_experience')

@server.route('/matching')
@login_required
def matching():
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in', 'danger')
        return redirect(url_for('login'))

    # Fetch user details
    cur = conn.cursor()
    cur.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    name, email = user

    # Fetch distinct industry experiences
    industries = df_exploded['industry_experience'].dropna().unique()

    return render_template('matching.html', user_id=user_id, name=name, email=email, industries=industries)

@server.route('/get_matches', methods=['POST'])
@login_required
def get_matches():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 401

    data = request.json
    selected_type = data.get('type')
    selected_industry = data.get('industry')

    print(f"Received type: {selected_type}, industry: {selected_industry}")

    if not selected_type or not selected_industry:
        return jsonify({"error": "Please make all selections"}), 400

    filtered_df = df_exploded[df_exploded['industry_experience'] == selected_industry]

    if selected_type == 'business_partner':
        matches = filtered_df[filtered_df['user_id'] != user_id].head(5)
    elif selected_type == 'mentor':
        matches = filtered_df[filtered_df['user_id'] != user_id].sort_values(by='entrepreneurial_experience', ascending=False).head(5)

    print(f"Matches found: {matches}")

    results = matches.to_dict(orient='records')
    return jsonify(results)


@server.route('/user_profile')
@login_required
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('User not logged in', 'danger')
        return redirect(url_for('login'))

    # Fetch user details from the users table
    cur = conn.cursor()
    cur.execute("SELECT name, email FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('login'))

    # Fetch onboarding details from the onboarding table
    cur.execute("SELECT * FROM onboarding_entries WHERE user_id = %s", (user_id,))
    onboarding = cur.fetchone()

    return render_template('user_profile.html', user=user, onboarding=onboarding)



@server.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html')

@server.route('/calculate')
def calculate():
    result = calculate_alignment_scores()
    return result

@server.route('/get_cxo_scores/<selected_user>')
def get_cxo_scores(selected_user):
    try:
        print(f"Selected user: {selected_user}")
        cur.execute("""
            SELECT "CEO", "CSO", "CPO", "CMO", "CFO", "CTO", "COO", "Advisor"
            FROM cxo_scores_result
            WHERE user_id = %s
        """, (selected_user,))
        
        scores = cur.fetchone()
        if scores:
            score_dict = dict(zip(['CEO', 'CSO', 'CPO', 'CMO', 'CFO', 'CTO', 'COO', 'Advisor'], scores))
            return jsonify(score_dict)
        else:
            return jsonify({"error": "No scores found for the specified user."}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    server.run(debug=True)

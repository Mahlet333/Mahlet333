from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json
from gsHandler import retrieve_data, create_new_sheet, create_new_page, append_row, update_row
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State, MATCH
import plotly.express as px
import pandas as pd
from sshtunnel import SSHTunnelForwarder
import psycopg2
from functools import wraps
import datetime
import os
import csv


def get_db_connection():
    server = SSHTunnelForwarder(
        ('letsrise.myonline.works', 22),  # SSH server and port
        ssh_username='ubuntu',  # SSH username
        ssh_pkey='~/.ssh/id_letsrise',  # Path to your private key
        remote_bind_address=('localhost', 5432)  # Database server and port
    )

    server.start()

    conn = psycopg2.connect(
        dbname='letsrise_v1',
        user='letsrise_intern',
        password='letsrise',
        host='localhost',
        port=server.local_bind_port  # Use the dynamically assigned local port
    )
    return conn, server

conn, server = get_db_connection()
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
query3 = """
SELECT * FROM public.user_info
ORDER BY user_id ASC; 
"""
cur = conn.cursor()
consequence_df = pd.read_sql(query1, conn)
comparison_df = pd.read_sql(query2, conn)
df = pd.read_sql(query3, conn)

consequence_df = consequence_df.loc[:, ~consequence_df.columns.duplicated()]
required_columns = ['user_id', 'name', 'email', 'age', 'linkedin_url', 'education_level', 'employment_status', 'entrepreneurial_experience', 'current_startup_stage', 'number_of_startups', 'role_in_entrepreneurship', 'industry_experience', 'number_of_previous_startups', 'location', 'gender', 'startup_name', 'assessment_id', 
                    'customer_centric', 'collaborative', 'agile', 'innovative', 'risk_taking', 'visionary', 'hustler', 'passionate', 'resilient', 'educational', 'analytical', 'frugal', 'legacy', 'digital', 'problem_solver', 
                    'delayed_product_market_fit', 'lack_of_product_market_fit', 'unable_to_complete_fundraise', 'lack_of_growth', 'lack_of_revenue', 'high_turnover_of_talent', 'inefficient_processes', 'time_consuming_client_acquisition', 'low_customer_conversion', 'low_customer_satisfaction', 'low_customer_retention', 'high_cash_burnrate', 'high_team_conflict', 'high_key_man_risk', 'lack_of_partnerships_collaborations', 'lack_of_scalability', 'lack_of_data_integrity', 'lack_of_data_security', 'lack_of_marketing', 'lack_of_motivation', 'lack_of_leadership', 'lack_of_innovation', 'lack_of_clarity', 'too_much_dependency_on_external_factors', 'lack_of_technological_advancements', 'lack_of_unique_value_proposition', 'lack_of_customer_variety', 'lack_of_intellectual_property', 'lacking_solution_quality', 'lack_of_supporters', 'missed_opportunities', 'delayed_revenue']
filtered_df = consequence_df[required_columns]
df_exploded = df.assign(industry_experience=df['industry_experience'].str.split('\n')).explode('industry_experience')

# Initialize Flask
server = Flask(__name__)
server.secret_key = 'supersecretkey' 


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

# Load questions from JSON
questions = read_questions_from_json('assessment_google_sheet.json')



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

# dash for matching users
dash_app2 = Dash(__name__, server=server, url_base_pathname='/dash2/')

dash_app2.layout = html.Div(style={'backgroundColor': '#f7f7f7', 'fontFamily': 'Poppins, sans-serif'}, children=[
    dcc.Dropdown(
        id='user-dropdown',
        options=[{'label': name, 'value': user_id} for user_id, name in zip(df['user_id'].unique(), df['name'].unique())],
        placeholder="Select a User",
        style={'marginBottom': '10px'}
    ),
    dcc.Dropdown(
        id='type-dropdown',
        options=[
            {'label': 'Business Partner', 'value': 'business_partner'},
            {'label': 'Mentor', 'value': 'mentor'}
        ],
        placeholder="Select Type",
        style={'marginBottom': '10px'}
    ),
    dcc.Dropdown(
        id='industry-dropdown',
        placeholder="Select Industry Experience",
        style={'marginBottom': '20px'}
    ),
    html.Div(id='results', style={'color': '#111', 'padding': '20px', 'border': '1px solid #ccc', 'borderRadius': '5px', 'boxShadow': '0 1px 3px rgba(0, 0, 0, 0.1)', 'backgroundColor': '#fff'}),
])

# Callback to update the industry dropdown based on the unique values in the DataFrame
@dash_app2.callback(
    Output('industry-dropdown', 'options'),
    Input('type-dropdown', 'value')
)
def set_industry_options(selected_type):
    if selected_type:
        unique_industries = df_exploded['industry_experience'].dropna().unique()
        return [{'label': industry, 'value': industry} for industry in unique_industries]
    return []

# Callback to update the results based on selected user, type, and industry experience
@dash_app2.callback(
    Output('results', 'children'),
    [Input('user-dropdown', 'value'),
     Input('type-dropdown', 'value'),
     Input('industry-dropdown', 'value')]
)
def update_results(selected_user, selected_type, selected_industry):
    if not selected_user or not selected_type or not selected_industry:
        return "Please make all selections."

    filtered_df = df_exploded[df_exploded['industry_experience'] == selected_industry]
    
    if selected_type == 'business_partner':
        top_5 = filtered_df[filtered_df['user_id'] != selected_user].head(5)
    elif selected_type == 'mentor':
        top_5 = filtered_df[filtered_df['user_id'] != selected_user].sort_values(by='entrepreneurial_experience', ascending=False).head(5)
    
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.P(f"{row['name']} - {row['industry_experience']} - {row['entrepreneurial_experience']} years of experience"),
                    html.Button('Introduce', id={'type': 'introduce-button', 'index': idx}, n_clicks=0, style={'float': 'right'})
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
                html.Div(id={'type': 'email-form', 'index': idx}, style={'display': 'none'})
            ])
        ]) for idx, row in top_5.iterrows()
    ])

# Callback to show the email form when the button is clicked
@dash_app2.callback(
    Output({'type': 'email-form', 'index': MATCH}, 'style'),
    Input({'type': 'introduce-button', 'index': MATCH}, 'n_clicks'),
    State({'type': 'email-form', 'index': MATCH}, 'style'),
    prevent_initial_call=True
)
def show_email_form(n_clicks, current_style):
    if n_clicks > 0:
        return {'display': 'block', 'paddingTop': '10px'}
    return current_style

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

                # Fetch user progress
                cur.execute("SELECT current_question FROM user_progress WHERE user_id=%s", (user[1],))
                progress = cur.fetchone()

                if progress:
                    session['current_question'] = progress[0]  # Start from the saved progress
                else:
                    # Insert a new row for the new user
                    cur.execute("INSERT INTO user_progress (user_id, current_question) VALUES (%s, 1)", (user[1],))
                    conn.commit()
                    session['current_question'] = 1  # Start from the first question

                return render_template('homepage.html')  # Render the homepage template with JavaScript
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
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            flash('User not logged in', 'danger')
            return redirect(url_for('login'))

        # Debug: Print form data for troubleshooting
        for key, value in request.form.items():
            print(f"{key}: {value}")

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

            print("All form data captured correctly.")

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

            print("Data inserted into onboarding_entries table.")

            cur.execute("UPDATE users SET onboarding_form_completed = TRUE WHERE user_id = %s", (user_id,))
            conn.commit()

            print("User form_completed status updated and transaction committed.")

            flash('Form submitted successfully!', 'success')
            return redirect(url_for('homepage'))
        except Exception as e:
            conn.rollback()
            print(f"Error submitting form: {e}")
            flash(f'Error submitting form: {e}', 'danger')
    return render_template('onboarding.html')


@server.route('/quiz')
@login_required
def quiz():
    # Get current question from session or default to 0
    current_question = session.get('current_question', 0)

    return render_template('quiz.html', questions=questions, current_question=current_question)

@server.route('/save_progress', methods=['POST'])
def save_progress():
    data = request.json
    current_question = data.get('current_question')
    user_id = session.get('user_id')

    if user_id and current_question:
        cur.execute("UPDATE user_progress SET current_question=%s WHERE user_id=%s", (current_question, user_id))
        conn.commit()
        return jsonify({'status': 'success'}), 200
    else:
        return jsonify({'status': 'error'}), 400



@server.route('/get_questions', methods=['GET'])
def get_questions():
    user_id = session.get('user_id')
    current_question = session.get('current_question')

    if user_id and current_question:
        questions_data = questions[current_question-1:]
        return jsonify({'questions': questions_data, 'current_question': current_question}), 200
    else:
        return jsonify({'status': 'error'}), 400


@server.route('/submit_quiz', methods=['POST'])
@login_required
def submit_quiz():
    data = request.get_json()
    answers = data.get('answers', [])

    if not answers:
        return jsonify({"message": "No answers provided."}), 400
    append_row("1yskiCZUdBlEp4PMbCVoO7981MBgSGwjnuPOLeBkieTo", "test", answers)
    # Reset progress in session after quiz submission
    session.pop('current_question', None)

    return jsonify({"message": "Quiz submitted successfully!"})

@server.route('/matching')
@login_required
def matching():
    return render_template('matching.html')

@server.route('/user_profile')
@login_required
def profile():
    return render_template('user_profile.html')

@server.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html')


def calculate_alignment_scores():
    json_export_path = 'assessment_google_sheet.json'
    debug_csv_path = '/Users/mahletatrsawandargei/Desktop/alignment_debug.csv'
    alignment_csv_path = '/Users/mahletatrsawandargei/Desktop/user_alignment_scores.csv'

    try:
        conn, server = get_db_connection()
        cursor = conn.cursor()

        if not os.path.exists(json_export_path):
            return f'Error: Exported JSON file not found at {json_export_path}'

        with open(json_export_path) as f:
            json_data = json.load(f)

        cursor.execute("""
            SELECT user_id, question1, question2, question3, question4, question5, question6, question7,
                   question8, question9, question10, question11, question12, question13, question14, 
                   question15, question16, question17, question18, question19, question20, question21, 
                   question22, question23, question24, question25, question26, question27, question28, 
                   question29, question30, question31, question32, question33, question34, question35, 
                   question36, question37, question38, question39, question40, question41, question42, 
                   question43, question44, question45 
            FROM assessment_entries
        """)

        assessment_entries = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        cursor.execute("""
            SELECT "Question_Number", "CEO_5", "CEO_4", "CEO_3", "CEO_2", "CEO_1",
                   "CSO_5", "CSO_4", "CSO_3", "CSO_2", "CSO_1",
                   "CPO_5", "CPO_4", "CPO_3", "CPO_2", "CPO_1",
                   "CMO_5", "CMO_4", "CMO_3", "CMO_2", "CMO_1",
                   "CFO_5", "CFO_4", "CFO_3", "CFO_2", "CFO_1",
                   "CTO_5", "CTO_4", "CTO_3", "CTO_2", "CTO_1",
                   "COO_5", "COO_4", "COO_3", "COO_2", "COO_1",
                   "Advisor_5", "Advisor_4", "Advisor_3", "Advisor_2", "Advisor_1"
            FROM cxo_alignment
        """)

        cxo_alignment_data = cursor.fetchall()
        cxo_alignment_dict = {row[0]: row[1:] for row in cxo_alignment_data}
        
        role_columns = ["CEO", "CSO", "CPO", "CMO", "CFO", "CTO", "COO", "Advisor"]

        with open(debug_csv_path, mode='w', newline='') as debug_csv_file:
            debug_csv_writer = csv.writer(debug_csv_file)
            debug_csv_writer.writerow(["user_id", "Question Number", "DB Decision Statement", "Matched JSON Decision Statement"])

            with open(alignment_csv_path, mode='w', newline='') as alignment_csv_file:
                alignment_csv_writer = csv.writer(alignment_csv_file)
                alignment_csv_writer.writerow(["user_id"] + role_columns)

                for entry in assessment_entries:
                    user_id = entry[0]
                    alignment_scores = {role: 0 for role in role_columns}
                    total_scores = {role: 0 for role in role_columns}
                    
                    for i in range(1, len(entry)):
                        question_number = str(i)
                        db_decision_statement = entry[i].strip().lower() if isinstance(entry[i], str) else str(entry[i]).strip().lower()
                        
                        # Remove extra quotation marks if present
                        if db_decision_statement.startswith('"') and db_decision_statement.endswith('"'):
                            db_decision_statement = db_decision_statement[1:-1]

                        matched_value = None
                        matched_json_statement = None

                        if question_number in json_data:
                            for statement in json_data[question_number]:
                                json_statement = statement["Decision Statement"].strip().lower()
                                if db_decision_statement == json_statement:
                                    matched_value = statement["Decision Statement Value"]
                                    matched_json_statement = json_statement
                                    break
                            

                        if matched_value is not None:
                            alignment_row = cxo_alignment_dict.get(int(question_number))
                            if alignment_row:
                                for j, role in enumerate(role_columns):
                                    role_score = alignment_row[j * 5 + (5 - matched_value)]
                                    alignment_scores[role] += role_score
                                    total_scores[role] += 5  # Assuming each question has a max score of 5

                        debug_csv_writer.writerow([user_id, question_number, entry[i], matched_json_statement])

                    alignment_percentages = {role: (alignment_scores[role] / total_scores[role] * 100) if total_scores[role] > 0 else 0
                                             for role in role_columns}

                    alignment_csv_writer.writerow([user_id] + [alignment_percentages[role] for role in role_columns])

                    # Round the scores and prepare the data for insertion into the database
                    rounded_scores = {role: round(alignment_percentages[role]) for role in role_columns}
                    rounded_scores['user_id'] = user_id

                    # Insert the scores into the database
                    cursor.execute("""
                        DELETE FROM cxo_scores_result WHERE user_id = %s
                    """, (user_id,))
                    
                    cursor.execute("""
                        INSERT INTO cxo_scores_result ("user_id", "CEO", "CSO", "CPO", "CMO", "CFO", "CTO", "COO", "Advisor")
                        VALUES (%(user_id)s, %(CEO)s, %(CSO)s, %(CPO)s, %(CMO)s, %(CFO)s, %(CTO)s, %(COO)s, %(Advisor)s)
                    """, rounded_scores)

        conn.commit()

        response = "<h2>Alignment Scores</h2>"
        response += "<ul>"
        for role in role_columns:
            response += f"<li>Role: {role}, Alignment Percentage: {alignment_percentages[role]:.2f}%</li>"
        response += "</ul>"

        return response

    except Exception as e:
        return f'Error: {str(e)}'

    finally:
        if 'conn' in locals():
            conn.close()

    return "Calculation completed successfully."

@server.route('/calculate_alignment', methods=['POST'])
def display_alignment_scores():
    result = calculate_alignment_scores()
    print("CXO Calculation Triggered")
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

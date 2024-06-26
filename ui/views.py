from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from .utils import read_model_options_from_excel
import ui.tco_model as tco
import os
import pickle
import json
# import matplotlib
# matplotlib.use('Agg')  # Use the 'Agg' backend for non-GUI rendering

def index(request):
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(project_dir, 'coating_details 1.xlsx')
    model_options = read_model_options_from_excel(file_path)
    param_files = get_param_files()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'run_simulation':
            return handle_run_simulation(request, model_options, project_dir)
        elif action == 'plot_coating_details':
            return handle_plot_coating_details(request, model_options)
        elif action == 'save_params':
            return save_params(request)
        elif action == 'load_params':
            return load_params(request)
        elif action == 'generate_report':
            return handle_generate_report(request, model_options, project_dir)

    return render(request, 'ui/index.html', {'model_options': model_options, 'param_files': param_files})


def handle_run_simulation(request, model_options, project_dir):
    form_data = request.POST
    num_rows = len([key for key in form_data if key.startswith('coating_model_')])
    combined_models = []
    message = ""
    image_url = None

    try:
        for i in range(num_rows):
            coating_type = form_data.get(f'coating_model_{i}')
            cleaning_option = form_data.get(f'cleaning_option_{i}')
            cleaning_frequency = form_data.get(f'cleaning_frequency_{i}')
            growth_type = form_data.get(f'growth_type_{i}')
            average_power = form_data.get(f'average_power_{i}')
            max_speed = form_data.get(f'max_speed_{i}')
            activity = form_data.get(f'activity_{i}')
            region = form_data.get(f'region_{i}')
            fuel_type = form_data.get(f'fuel_type_{i}')
            fouling_type = form_data.get(f'fouling_type_{i}')

            additional_params = {}
            additional_param_keys = form_data.getlist(f'additional_param_{i}')
            additional_param_values = form_data.getlist(f'param_value_{i}')
            for key, value in zip(additional_param_keys, additional_param_values):
                if value:
                    additional_params[key] = float(value)

            valid_params = {
                'coating_type': coating_type,
                'cleaning_frequency': int(cleaning_frequency) if cleaning_option == "Cleaning Frequency" else None,
                'fixed_cleanings': [int(x) for x in cleaning_frequency.split(',')] if cleaning_option == "Fixed Cleanings" else None,
                'growth_type': growth_type,
                'average_power': float(average_power),
                'max_speed': int(max_speed),
                'activity_rate': float(activity),
                'region': region,
                
                'fuel_type': fuel_type,
                'fouling_type': fouling_type,
                'reactive_cleaning': 10 if cleaning_option == "Reactive Cleaning" else None,
            }
            valid_params.update(additional_params)
            model_params = {k: v for k, v in valid_params.items() if v is not None}
            model_instance = tco.tco_model(**model_params)
            combined_models.append(model_instance)
        vessel_type = form_data.get('vessel_type')
        dwt = int(form_data.get('dwt'))
        distance_travelled = int(form_data.get('distance_travelled'))   

        tco.plot_results_obj_list(models=combined_models, no_power_details=False, col="power_change", growth_type=growth_type, show_table=True, save=False)
        image_url = 'static/ui/simulation_results.png'
        message = "Simulation completed successfully."
    except Exception as e:
        message = f"An error occurred: {e}"

    return render(request, 'ui/index.html', {'model_options': model_options, 'message': message, 'image_url': image_url, 'param_files': get_param_files()})
def handle_generate_report(request, model_options, project_dir):
    form_data = request.POST
    num_rows = len([key for key in form_data if key.startswith('coating_model_')])
    combined_models = []
    message = ""
    report_url = None

    try:
        for i in range(num_rows):
            coating_type = form_data.get(f'coating_model_{i}')
            cleaning_option = form_data.get(f'cleaning_option_{i}')
            cleaning_frequency = form_data.get(f'cleaning_frequency_{i}')
            growth_type = form_data.get(f'growth_type_{i}')
            average_power = form_data.get(f'average_power_{i}')
            max_speed = form_data.get(f'max_speed_{i}')
            activity = form_data.get(f'activity_{i}')
            region = form_data.get(f'region_{i}')
            fuel_type = form_data.get(f'fuel_type_{i}')
            fouling_type = form_data.get(f'fouling_type_{i}')

            additional_params = {}
            additional_param_keys = form_data.getlist(f'additional_param_{i}')
            additional_param_values = form_data.getlist(f'param_value_{i}')
            for key, value in zip(additional_param_keys, additional_param_values):
                if value:
                    additional_params[key] = float(value)

            valid_params = {
                'coating_type': coating_type,
                'cleaning_frequency': int(cleaning_frequency) if cleaning_option == "Cleaning Frequency" else None,
                'fixed_cleanings': [int(x) for x in cleaning_frequency.split(',')] if cleaning_option == "Fixed Cleanings" else None,
                'growth_type': growth_type,
                'average_power': float(average_power),
                'max_speed': int(max_speed),
                'activity_rate': float(activity),
                'region': region,
                'fuel_type': fuel_type,
                'fouling_type': fouling_type,
                'reactive_cleaning': 10 if cleaning_option == "Reactive Cleaning" else None,
            }
            valid_params.update(additional_params)
            model_params = {k: v for k, v in valid_params.items() if v is not None}
            model_instance = tco.tco_model(**model_params)
            combined_models.append(model_instance)

        # Ensure the media directory exists
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)

        output_path = os.path.join(settings.MEDIA_ROOT, 'output.pdf')
        tco.create_report(combined_models, output_path=output_path, debug=True)
        report_url = settings.MEDIA_URL + 'output.pdf'
        message = "Report generated successfully."
    except Exception as e:
        message = f"An error occurred: {e}"

    return render(request, 'ui/index.html', {'model_options': model_options, 'message': message, 'report_url': report_url, 'param_files': get_param_files()})
def handle_plot_coating_details(request, model_options):
    form_data = request.POST
    num_rows = len([key for key in form_data if key.startswith('coating_model_')])
    combined_models = []
    message = ""

    try:
        for i in range(num_rows):
            coating_type = form_data.get(f'coating_model_{i}')
            cleaning_option = form_data.get(f'cleaning_option_{i}')
            cleaning_frequency = form_data.get(f'cleaning_frequency_{i}')
            growth_type = form_data.get(f'growth_type_{i}')
            average_power = form_data.get(f'average_power_{i}')
            max_speed = form_data.get(f'max_speed_{i}')
            activity = form_data.get(f'activity_{i}')
            region = form_data.get(f'region_{i}')
            fuel_type = form_data.get(f'fuel_type_{i}')
            fouling_type = form_data.get(f'fouling_type_{i}')

            additional_params = {}
            additional_param_keys = form_data.getlist(f'additional_param_{i}')
            additional_param_values = form_data.getlist(f'param_value_{i}')
            for key, value in zip(additional_param_keys, additional_param_values):
                if value:
                    additional_params[key] = float(value)

            valid_params = {
                'coating_type': coating_type,
                'cleaning_frequency': int(cleaning_frequency) if cleaning_option == "Cleaning Frequency" else None,
                'fixed_cleanings': [int(x) for x in cleaning_frequency.split(',')] if cleaning_option == "Fixed Cleanings" else None,
                'growth_type': growth_type,
                'average_power': float(average_power),
                'max_speed': int(max_speed),
                'activity_rate': float(activity),
                'region': region,
                'fuel_type': fuel_type,
                'fouling_type': fouling_type,
                'reactive_cleaning': 10 if cleaning_option == "Reactive Cleaning" else None,
            }
            valid_params.update(additional_params)
            model_params = {k: v for k, v in valid_params.items() if v is not None}
            model_instance = tco.tco_model(**model_params)
            combined_models.append(model_instance)

    
        for model in combined_models:
            tco.plot_coating_details(
                combined_models,
                metrics=['power_change', 'power_output', 'coating_thickness', 'coating_roughness'],
                save=False,
                debug=False
            )
        message = "Coating details plotted successfully."
    except Exception as e:
        message = f"An error occurred: {e}"

    return render(request, 'ui/index.html', {'model_options': model_options, 'message': message, 'param_files': get_param_files()})

def save_params(request):
    if request.method == 'POST':
        params = json.loads(request.body.decode('utf-8'))
        filename = params.pop('filename')

        if not os.path.exists('params'):
            os.makedirs('params')

        with open(f'params/{filename}.pkl', 'wb') as f:
            pickle.dump(params, f)

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'fail'}, status=400)

def load_params(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        filename = data.get('filename')

        with open(f'params/{filename}', 'rb') as f:
            params = pickle.load(f)

        return JsonResponse(params, safe=False)
    return JsonResponse({'status': 'fail'}, status=400)

def get_param_files():
    param_dir = 'params'
    if not os.path.exists(param_dir):
        os.makedirs(param_dir)
    return [f for f in os.listdir(param_dir) if f.endswith('.pkl')]

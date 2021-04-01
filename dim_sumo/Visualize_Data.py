import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.table as tbl
import matplotlib
import numpy as np
import copy as cp
import os
from matplotlib.font_manager import FontProperties
from pymongo import MongoClient
from datetime import date


## Plots heatmaps for a set of facts within a range of frequencies using all combinations of frequencies
def plot_by_frequencies(result, facts=["queue_1", "queue_3"], titles=None, valid_frequencies = [0.25, 0.5, 0.75, 1], substract_base = 0):
    
    num_facts = len(facts)
    titles = facts if titles is None else titles
    
    cell_font = FontProperties(size=20, family='sans-serif')

    for freq_1 in valid_frequencies:
        for freq_3 in valid_frequencies:
            cond_1 = result["freq_1"] == freq_1
            cond_2 = result["freq_3"] == freq_3
            data = result[cond_1 & cond_2]            
            X = data["prob_1"].unique()
            Y = data["prob_3"].unique()
            X.sort()
            Y.sort()
            
            fig, axes = plt.subplots(1, num_facts)
            fig.set_size_inches((12 * num_facts,12))
            
            for i, fact in enumerate(facts):           
                Z = pd.pivot_table(data, index="prob_1", columns="prob_3", values=fact).round(2)
                ax = axes[i]
            
                table = tbl.Table(ax, loc="best")
                ax.set_title(titles[i] + " - {Y:A:"+str(round(1/freq_1,2))+"Hz:[0,100]%} - " + " {X:B:" + str(round(1/freq_3,2))+"Hz:[0,100]%}", 
                             fontsize=20)
                ax.tick_params(labelsize=20)
                            
                min_value = Z.min().min()
                max_value = Z.max().max()
                norm = matplotlib.colors.Normalize(vmin=min_value-substract_base, vmax=max_value-substract_base)
                cmap = plt.get_cmap("coolwarm") # plt.get_cmap("OrRd")
                
                for i, prob_1 in enumerate(Z.index[::-1]):
                    for j, prob_3 in enumerate(Z.columns):                        
                        val = Z[prob_3][prob_1]
                        val = val - substract_base
                        size = 0.0965
                        color = cmap(norm(val))
                        table.add_cell(i, j, size, size, text=str(val), facecolor=color, fontproperties=cell_font)
        
                ax.set_xlabel("Prob. deceiver movement B", fontsize=30)
                ax.set_ylabel("Prob. deceiver movement A", fontsize=30)
                ax.add_table(table)
            
    plt.show()

## Plots lines for one probability of deceivers in a lane against all probabilities in the other
def plot_tendency(result, facts=["queue_1", "queue_3"], titles=None, valid_frequencies = [0.25, 0.5, 0.75, 1], 
                  substract_base = 0, formats=None, normalize=False):
    
    num_facts = len(facts)
    titles = facts if titles is None else titles
    formats = np.full(len(titles), "bo") if formats is None else formats
    
    for i, freq_1 in enumerate(valid_frequencies):
        for freq_3 in valid_frequencies[i:]:
            cond_1 = result["freq_1"] == freq_1
            cond_2 = result["freq_3"] == freq_3
            data = result[cond_1 & cond_2]
            X = data["prob_1"].unique()
            Y = data["prob_3"].unique()
            X.sort()
            Y.sort()
            
            fig, axes = plt.subplots(1, num_facts)
            fig.set_size_inches((15 * num_facts,15))
            
            for i, fact in enumerate(facts):           
                Z = pd.pivot_table(data, index="prob_1", columns="prob_3", values=fact).round(2)
                
                Z = Z - substract_base
                
                if normalize:
                    Z = Z * 100 / Z.max().max()
                
                ax = axes[i]
                
                for j, column in enumerate(Z.columns):
                    ax.plot(Z[column], formats[j], markersize=12, linewidth=4)
                
                # ax.set_title(titles[i] + " - {Y:A:"+str(round(1/freq_1,2))+"Hz:[0,100]%} - " + " {X:B:" + str(round(1/freq_3,2))+"Hz:[0,100]%}", fontsize=20)
                
                ax.legend(np.round(Y,1), fontsize=25, title="$Probability_B$", title_fontsize="25")
                ax.tick_params(labelsize=25, which="major")
                ax.set_xticks([0.0,0.25,0.5,0.75,1.0])

                ax.set_xlabel("$Probability_A$", fontsize=30)
                ax.set_ylabel(titles[i], fontsize=30)
            plt.show()
            
    
    
def plot_boxplot(sim_query_obj, veh_query_obj, variable, values, title="", num_experiments=None, substract_base = 0, db=MongoClient().tesis_DIM, show_outliers = True, tolerance = 0.001, debug = False, to_file=None, exp_suffix="", delay_range=[0,200]):
    sim_query_obj = cp.copy(sim_query_obj)
    veh_query_obj = cp.copy(veh_query_obj)
    values = cp.copy(values)
    sim_query_obj["done"] = True
    
    data = []

    for val in values:
        # Get the ids of the simulation runs to consider            
        sim_query_obj[variable] = { "$gt" : val - tolerance, "$lt" : val + tolerance }
        print(sim_query_obj) if debug else None
        ids = db["sim" + exp_suffix].find(sim_query_obj, { "_id":1 }).distinct("_id")[0:num_experiments]
        print("Sim ids:", ids) if debug else None
        veh_query_obj["run_id"] = { "$in" : ids }
        print(veh_query_obj) if debug else None
        # Get the details for the selected simulations     
        delays = db["sim_vehicles" + exp_suffix].find(veh_query_obj, 
                                     { "_id" : 0, "delay":1 })
        delays = pd.DataFrame(list(delays))
        
        if "delay" not in delays:
            delays["delay"] = 0
        data.append(delays["delay"]-substract_base)

    fig, axes = plt.subplots()
    fig.set_size_inches((15, 15))
    axes.tick_params(labelsize=25)
    axes.set_xlabel("$Probability_A$", fontsize=30)
    axes.set_ylabel(title, fontsize=30)
    # axes.set_title(title + " - {Y:A:"+str(round(1/sim_query_obj["freq_1"],2))+"Hz:[0,100]%} - " + " {X:B:" + str(round(1/sim_query_obj["freq_3"],2))+"Hz:"+str(sim_query_obj["prob_3"]*100)+"%}", fontsize=20)
    bp_dict = axes.boxplot(data, notch=True, labels=values.round(2), showfliers=show_outliers, showmeans=True)
    
    # Code taken from https://stackoverflow.com/questions/18861075/overlaying-the-numeric-value-of-median-variance-in-boxplots
    for line in bp_dict['medians']:
        # get position data for median line
        x, y = line.get_xydata()[0] # top of median line
        # overlay median value
        axes.text(x, y, '%.1f' % y,
             horizontalalignment='left',
             verticalalignment='bottom') # draw above, centered

    for line in bp_dict['boxes']:
        x, y = line.get_xydata()[0] # bottom of left line
        axes.text(x,y, '%.1f' % y,
             horizontalalignment='center', # centered
             verticalalignment='top')      # below
        x, y = line.get_xydata()[6] # bottom of right line
        axes.text(x,y, '%.1f' % y,
             horizontalalignment='center', # centered
                 verticalalignment='bottom')      # below

    for point in bp_dict['means']:
        x, y = point.get_xydata()[0] # bottom of left line
        axes.text(x,y, '%.1f' % y,
             horizontalalignment='left', # centered
             verticalalignment='bottom')      # below
        
    # Set the range of the Y axis
    axes.set_ylim(delay_range)
    
    if to_file is None:
        plt.show()
    else:
        plt.savefig(to_file)
        
def plot_histogram(sim_query_obj, veh_query_obj, variable, value, title="", num_experiments=None, substract_base = 0, db=MongoClient().tesis_DIM, tolerance = 0.001, debug = False, to_file=None, exp_suffix="", delay_range=[0,200]):
    sim_query_obj = cp.copy(sim_query_obj)
    veh_query_obj = cp.copy(veh_query_obj)
    sim_query_obj["done"] = True
    
    # Get the ids of the simulation runs to consider            
    sim_query_obj[variable] = { "$gt" : value - tolerance, "$lt" : value + tolerance }
    print(sim_query_obj) if debug else None
    ids = db["sim" + exp_suffix].find(sim_query_obj, { "_id":1 }).distinct("_id")[0:num_experiments]
    print(ids) if debug else None
    veh_query_obj["run_id"] = { "$in" : ids }
    print(veh_query_obj) if debug else None
    # Get the details for the selected simulations     
    delays = db["sim_vehicles" + exp_suffix].find(veh_query_obj, 
                                 { "_id" : 0, "delay":1 })
    delays = pd.DataFrame(list(delays))
    
    if "delay" not in delays:
        delays["delay"] = 0
    delays["delay"] = delays["delay"]-substract_base

    fig, axes = plt.subplots()
    fig.set_size_inches((15, 15))
    axes.tick_params(labelsize=25)
    axes.set_xlabel(title, fontsize=30)
    axes.set_ylabel("Acumulated proportion of vehicles", fontsize=30)
    # axes.set_title(title + " - {Y:A:"+str(round(1/sim_query_obj["freq_1"],2))+"Hz:[0,100]%} - " + " {X:B:" + str(round(1/sim_query_obj["freq_3"],2))+"Hz:"+str(sim_query_obj["prob_3"]*100)+"%}", fontsize=20)
    axes.hist(delays["delay"], bins=20, density=True)
    # Set the range of the X axis
    axes.set_xlim(delay_range)
    
    if to_file is None:
        plt.show()
    else:
        plt.savefig(to_file)        


def plot_tendencies_delay_and_count(valid_freqs=[0.5, 1.0], valid_probs=[0.0, 0.5, 1.0]):    
    # Load the results
    result = pd.read_csv("results/wave 009 - Exponential 30 mins full/from_mongo_600s_to_1800s_by_start_line_and_freqs1.5-2.0.csv")
    
    # Add a columns for the the average times for all, deceivers and not_deceivers
    result["avg_time_all_1"] = result["everyone_time_1"] / result["everyone_count_1"]
    result["avg_time_all_3"] = result["everyone_time_3"] / result["everyone_count_3"]
    result["avg_time_deceivers_1"] = result["deceivers_time_1"] / result["deceivers_count_1"]
    result["avg_time_honest_1"] = result["honest_time_1"] / result["honest_count_1"]
    result["avg_time_all"] = (result["everyone_time_1"] + result["everyone_time_3"]) / (result["everyone_count_1"] + result["everyone_count_3"])
    result["avg_time_deceivers"] = (result["deceivers_time_1"]+result["deceivers_time_3"]) / (result["deceivers_count_1"]+result["deceivers_count_3"])
    result["avg_time_honest"] = (result["honest_time_1"]+result["honest_time_3"]) / (result["honest_count_1"]+result["honest_count_3"])
    result["everyone_count" ] = result["everyone_count_1"] + result["everyone_count_3"]
    result["queue_both"] = result["queue_1"]+result["queue_3"]
    
    result = result[result["prob_3"].isin(valid_probs)]
    
#    plot_tendency(result, 
#                        facts=["avg_time_all", "avg_time_all_1", "avg_time_all_3"],
#                        titles=["Avg delay All (s)", "Avg delay lane A (s)", "Avg delay lane B (s)"],
#                        valid_frequencies=valid_freqs, substract_base=24,
#                        formats=[":s", ":v", ":>", ":h", ":*"])
    plot_tendency(result, 
                        facts=["everyone_count", "everyone_count_1", "everyone_count_3"],
                        titles=["Proportion of max vehicles both lanes [%]", "Proportion of max  vehicles lane A [%]", "Proportion of max vehicles lane B [%]"],
                        valid_frequencies=valid_freqs, 
                        formats=[":s", ":>", ":h", ":v", ":*"],
                        normalize=True)

def plot_box_delays(freq_1, freq_3, prob_3, deceiver_value = None, to_file_prefix=None, movements=[], warmup_time=0, exp_suffix="", delay_range=[0,200]):
    sim_query = {"freq_1" : freq_1, "freq_3" : freq_3, "prob_3" : prob_3}
    vehicle_query = { "start_time" : { "$gt" : warmup_time } }
    show_outliers = True
    prob_1_values = np.linspace(0.0, 1, 6).round(1)
    num_experiments = None
    debug = True
        
    # Check if we should present just some of the values for deceivers or not deceivers
    if not deceiver_value is None:
        vehicle_query["deceiver"] = deceiver_value
        
    for movement in movements:
        plot_boxplot(
            sim_query,
            { "$and" : [ { "movement":movement }, vehicle_query ] },
            "prob_1",
            prob_1_values,
            num_experiments=num_experiments,
            title="Avg delay " + movement + " [s] veh/h: " + str(freq_1),
            show_outliers=show_outliers,
            debug = debug,
            to_file = None if to_file_prefix is None else to_file_prefix + "_" + movement.replace(">", "") + ".png",
            exp_suffix=exp_suffix,
            delay_range=delay_range
        )
    
    plot_boxplot(
        sim_query,
        vehicle_query,
        "prob_1",
        prob_1_values,
        num_experiments=num_experiments,
        title="Avg delay All [s] veh/h: " + str(freq_1),
        show_outliers=show_outliers,
        debug = debug,
        to_file = None if to_file_prefix is None else to_file_prefix + "_ALL.png",
        exp_suffix=exp_suffix,
        delay_range=delay_range
    )

def plot_histogram_delays(freq_1, freq_3, prob_1, prob_3, deceiver_value = None, to_file_prefix=None, movements=[], warmup_time=0, exp_suffix="", delay_range=[0,200]):
    sim_query = {"freq_1" : freq_1, "freq_3" : freq_3, "prob_1" : prob_1}
    vehicle_query = { "start_time" : { "$gt" : warmup_time } }
    num_experiments = None
    debug = False
        
    # Check if we should present just some of the values for deceivers or not deceivers
    if not deceiver_value is None:
        vehicle_query["deceiver"] = deceiver_value
   
    for movement in movements:
        plot_histogram(
            sim_query,
            { "$and" : [ { "movement":movement }, vehicle_query ] },
            "prob_3",
            prob_3,
            num_experiments=num_experiments,
            title="Avg delay " + movement + " [s] veh/h: " + str(freq_1),
            debug = debug,
            to_file = None if to_file_prefix is None else to_file_prefix + "_" + movement.replace(">", "") + "_hist.png",
            exp_suffix=exp_suffix,
            delay_range=delay_range
        )
    
    plot_histogram(
        sim_query,
        vehicle_query,
        "prob_3",
        prob_3,
        num_experiments=num_experiments,
        title="Avg delay All [s] veh/h: " + str(freq_1),
        debug = debug,
        to_file = None if to_file_prefix is None else to_file_prefix + "_ALL_hist.png",
        exp_suffix=exp_suffix,
        delay_range=delay_range
    )

experiment_suffix = ""
freq_1 = 700
freq_3 = 400
delay_range = [0, 800]
warmup_time = 60 * 15 # In seconds
today = date.today().isoformat()
movements_all = ["N->S", "W->E"]

directory = "./data/digest/" + today + experiment_suffix + "_vph_" + str(freq_1) + "_" + str(freq_3)  + "/" 
if not os.path.exists(directory):
    os.makedirs(directory)
plot_box_delays(freq_1=freq_1, freq_3=freq_3, prob_3=0.0, movements=movements_all, to_file_prefix=directory+"all", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)
# plot_box_delays(freq_1=freq_1, freq_3=freq_3, prob_3=0.2, movements=movements_all, deceiver_value=False, to_file_prefix=directory+"no", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)
plot_histogram_delays(freq_1=freq_1, freq_3=freq_3, prob_1=0.0, prob_3=0.0, movements=movements_all, to_file_prefix=directory+"all_0", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)
plot_histogram_delays(freq_1=freq_1, freq_3=freq_3, prob_1=0.4, prob_3=0.0, movements=movements_all, to_file_prefix=directory+"all_1", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)
#plot_histogram_delays(freq_1=freq_1, freq_3=freq_3, prob_1=0.0, prob_3=0.0, deceiver_value=False, movements=movements_all, to_file_prefix=directory+"no_0", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)
#plot_histogram_delays(freq_1=freq_1, freq_3=freq_3, prob_1=0.0, prob_3=0.2, deceiver_value=False, movements=movements_all, to_file_prefix=directory+"no_1", warmup_time=warmup_time, exp_suffix=experiment_suffix, delay_range=delay_range)

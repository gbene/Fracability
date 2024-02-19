"""

Test survival analysis feasibility for multiple censored events.

1. Every event starts at the same point
2. Every event has a randomly distributed length following a lognormal distribution
3. Every event is censored at different values following a uniform distribution that shifts to the left (removing the same
amount each iteration). We end the shift only when 100% censoring is reached.

We test the effects of the % censoring on the fitting of a known distribution by plotting the % of censored values
with the sample average. We run n iterations and mean them to get an overall trend. This should provide a better plot
that shows the effect of censoring because we exclude the effect of random sampling on the estimation of the real mean.

"""

import scipy.stats as ss
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from numpy.random import Generator, PCG64
import time
sns.set_theme()


def plot_survival(start_times, end_times, censoring = None, name = None):
    """
    Function used to plot a survival diagram

    :param start_times: list of start times
    :param end_times: list of end times
    """

    if censoring is not None:
        if len(censoring) == 1:
            censoring_points = np.repeat(censoring, len(start_times))
        else:
            censoring_points = censoring

        for i, (start, end, censoring) in enumerate(zip(start_times, end_times, censoring_points)):
            plt.scatter(end, i, color='r', marker='^')
            plt.scatter(start, i, color='b', marker='o')
            plt.scatter(censoring, i, color='y', marker='|', s=100)
            plt.hlines(y=i, xmin=start, xmax=end)
    else:
        for i, (start, end) in enumerate(zip(start_times, end_times)):
            plt.scatter(end, i, color='r', marker='^')
            plt.scatter(start, i, color='b', marker='o')
            plt.hlines(y=i, xmin=start, xmax=end)
    # plt.savefig(name, dpi=200)
    plt.show()


def lognorm_parameters(target_mean, target_std):
    """
    Get the parameters of the underlying normal distribution for mean and std of the lognorm
    :param target_mean: Target lognorm mean
    :param target_std: Target lognorm std
    """

    var_normal = np.log((target_std ** 2 / (target_mean ** 2)) + 1)

    m_normal = np.log(target_mean) - var_normal / 2

    return m_normal, np.sqrt(var_normal)


distr = ss.lognorm
mean = 4.94
std = 6.52
n_lines = 1000
n_iterations = 10  # Number of iterations
seed = 12345
n_windows = 50  # number of windows used to censor the values
resample_line = np.arange(0, 100.1, 0.1)  # Values used to resample the mean values


iter_mean_everything_interpolated_list = np.empty((n_iterations, len(resample_line)))
iter_mean_nocensor_interpolated_list = np.empty((n_iterations, len(resample_line)))
iter_mean_censor_interpolated_list = np.empty((n_iterations, len(resample_line)))
iter_percentage_censoring_list = np.empty((n_iterations, n_windows))

mu_l, std_l = lognorm_parameters(mean, std)

sim_dict = {}
for i in range(n_iterations):
    print(f'iter: {i}', end='\r')

    percentage_censoring_list_raw = []
    percentage_censoring_list = []

    mean_everything_list_raw = []  # list of means for fitting all the data
    mean_everything_list = []  # list of means for fitting all the data

    mean_nocensor_list_raw = []  # list of means for fitting excluding censored data
    mean_nocensor_list = []  # list of means for fitting excluding censored data

    mean_censor_list_raw = []  # list of means for fitting using censoring
    mean_censor_list = []

    lengths = distr.rvs(s=std_l, scale=np.exp(mu_l), size=n_lines)

    sample_mean = np.mean(lengths)

    starts = np.zeros_like(lengths)

    ends = starts+lengths

    minimum_end = min(ends)  # Min start value
    maximum_end = max(ends)  # Max end value

    dataset = pd.DataFrame({'starts': starts, 'ends': ends, 'og': lengths,
                            'modified': lengths, 'censored': np.zeros_like(lengths)})
    n_total = len(dataset)

    censoring_list = ss.uniform.rvs(0, minimum_end,
                                    size=n_lines)  # Values where we censor the data


    min_censor = min(censoring_list)  # smallest censoring event
    max_censor = max(censoring_list)  # smallest censoring event
    # print(max(lengths/censoring_list))
    #
    # res = (maximum_end-min_censor)/n_windows  # quantity to remove
    # print(res)
    steps_list = []
    step = 0
    while True:
        # censoring_list[censoring_list <= 0] = ends[censoring_list <= 0]/10
        steps_list.append(step)
        indexes = np.where(dataset['ends'] >= censoring_list)
        dataset.loc[dataset.index[indexes], 'censored'] = 1  # Flag the values > than the censoring value
        dataset.loc[dataset.index[indexes], 'modified'] = censoring_list[indexes]  # Set the flagged value equal to the censoring value

        censored = dataset.loc[dataset['censored'] == 1, 'modified']  # Get censored values
        uncensored = dataset.loc[dataset['censored'] == 0, 'modified']  # Get uncensored values

        n_censored = len(censored)  # number of censored values
        # print(n_censored)
        # plot_survival(starts, ends, censoring_values, f"survp_{mean}_{std}.png")

        percentage_censored = 100*(n_censored/n_total)
        percentage_censoring_list_raw.append(percentage_censored)
        # print(percentage_censored, end='\r')

        # Fit everything

        params_all = distr.fit(dataset['modified'], floc=0)
        fitted_all = distr(*params_all)
        everything_diff = fitted_all.mean()-sample_mean
        mean_everything_list_raw.append(everything_diff)


        # Fit only non censored

        if len(uncensored) == 0:
            nocensor_diff = np.nan
        else:
            params_nocens = distr.fit(uncensored, floc=0)
            fitted_nocens = distr(*params_nocens)
            nocensor_diff = fitted_nocens.mean()-sample_mean

        mean_nocensor_list_raw.append(nocensor_diff)

        # Fit with censoring

        ss_dataset = ss.CensoredData(uncensored=uncensored, right=censored)

        params_cens = distr.fit(ss_dataset, floc=0)
        fitted_cens = distr(*params_cens)

        cens_diff = fitted_cens.mean() - sample_mean
        mean_censor_list_raw.append(cens_diff)

        # Construct interpolation dataset

        if percentage_censored not in percentage_censoring_list:
            mean_everything_list.append(everything_diff)

            mean_nocensor_list.append(nocensor_diff)

            mean_censor_list.append(cens_diff)

            percentage_censoring_list.append(percentage_censored)
        else:
            index = percentage_censoring_list.index(percentage_censored)

            mean_value_everything = np.mean([mean_everything_list[index], everything_diff])
            mean_everything_list[index] = mean_value_everything

            mean_value_nocens = np.mean([mean_nocensor_list[index], nocensor_diff])
            mean_nocensor_list[index] = mean_value_nocens

            mean_value_censor = np.mean([mean_censor_list[index], cens_diff])
            mean_censor_list[index] = mean_value_censor

        dataset['modified'] = dataset['og']  # Reset the values
        dataset['censored'] = 0  # Reset the censoring flag

        if percentage_censored == 0:
            break
        else:
            step += 1
            censoring_list *= 1.3
    interpolated_values_everything = np.interp(resample_line,
                                               percentage_censoring_list[::-1],
                                               mean_everything_list[::-1])

    iter_mean_everything_interpolated_list[i, :] = interpolated_values_everything

    interpolated_values_nocensor = np.interp(resample_line,
                                             percentage_censoring_list[::-1],
                                             mean_nocensor_list[::-1])

    iter_mean_nocensor_interpolated_list[i, :] = interpolated_values_nocensor

    interpolated_values_censoring = np.interp(resample_line,
                                              percentage_censoring_list[::-1],
                                              mean_censor_list[::-1])

    iter_mean_censor_interpolated_list[i, :] = interpolated_values_censoring

    # ax.plot(percentage_censoring_list, mean_everything_list, alpha=1/n_iterations, color='r')
    # ax.plot(percentage_censoring_list, mean_nocensor_list, alpha=1/n_iterations, color='b')
    # plt.plot(percentage_censoring_list_raw, mean_censor_list_raw, 'go')
    # plt.plot(percentage_censoring_list, mean_censor_list, 'bo')
    # plt.plot(resample_line, iter_mean_censor_interpolated_list[i], 'y-')
    # print(percentage_censoring_list_raw)
    plt.plot(steps_list, percentage_censoring_list_raw, 'k-o', markersize=2)
    plt.xlabel('Step (s)')
    plt.ylabel('% censored (p)')
    plt.savefig(f'images/interp/step_p_{i}.png', dpi=200)
    # plt.show()
    plt.plot(steps_list, mean_censor_list_raw, 'k-o', markersize=2)
    plt.xlabel('Step (s)')
    plt.ylabel('Delta')
    plt.savefig(f'images/interp/step_d_{i}.png', dpi=200)
    # plt.show()
    plt.plot(percentage_censoring_list_raw, mean_censor_list_raw, 'go')
    plt.plot(percentage_censoring_list_raw, mean_censor_list_raw, 'b-')
    plt.xlabel('% censoring')
    plt.ylabel('Delta')
    plt.savefig(f'images/interp/raw_{i}.png', dpi=200)
    # plt.show()
    plt.plot(percentage_censoring_list_raw, mean_censor_list_raw, 'go')
    plt.plot(percentage_censoring_list, mean_censor_list, 'bo')
    plt.plot(resample_line, iter_mean_censor_interpolated_list[i], 'y-')
    plt.xlabel('% censoring')
    plt.ylabel('Delta')
    plt.savefig(f'images/interp/interp_{i}.png', dpi=200)
    # plt.show()
    # sim_dict[i] = {'length': len(mean_everything_list), 'percentage_list': np.array(percentage_censoring_list),
    #                'mean_ev_list': np.array(mean_everything_list),
    #                'mean_nocens_list': np.array(mean_nocensor_list),
    #                'mean_cens_list': np.array(mean_censor_list)}


mean_everything_curve = np.mean(iter_mean_everything_interpolated_list, axis=0)
mean_nocensor_curve = np.mean(iter_mean_nocensor_interpolated_list, axis=0)
mean_censoring_curve = np.mean(iter_mean_censor_interpolated_list, axis=0)

std_percent_everything = np.std(iter_mean_everything_interpolated_list, axis=0)  # std for each censoring % step
std_percent_nocensor = np.std(iter_mean_nocensor_interpolated_list, axis=0)  # std for each censoring % step
std_percent_censor = np.std(iter_mean_censor_interpolated_list, axis=0)  # std for each censoring % step


# print(mean_censoring_curve)

# # print(test)
# print(sim_dict[1]['percentage_list'])
# print(sim_dict[1]['mean_cens_list'])
fig, ax = plt.subplots()
#
# ax.fill_between(resample_line, mean_everything_curve-std_percent_everything,
#                 mean_everything_curve+std_percent_everything,
#                 alpha=0.5, color='r')
#
# ax.plot(resample_line, mean_everything_curve, color='r', label='Fit using everything')
#
# ax.fill_between(resample_line, mean_nocensor_curve-std_percent_nocensor,
#                 mean_nocensor_curve+std_percent_nocensor,
#                 alpha=0.5, color='b')
# ax.plot(resample_line, mean_nocensor_curve, color='b', label='Fit using only complete values')

ax.fill_between(resample_line, mean_censoring_curve-(3*std_percent_censor),
                mean_censoring_curve+(3*std_percent_censor),
                alpha=1, color='r', label='3 sigma')
ax.fill_between(resample_line, mean_censoring_curve-(2*std_percent_censor),
                mean_censoring_curve+(2*std_percent_censor),
                alpha=1, color='g', label='2 sigma')
ax.fill_between(resample_line, mean_censoring_curve-std_percent_censor,
                mean_censoring_curve+std_percent_censor,
                alpha=1, color='y', label='1 sigma')
ax.plot(resample_line, mean_censoring_curve, color='k', label='Fit using survival')

inspection_value = 8.9
inspection_value_idx = np.where(resample_line == inspection_value)[0][0]  # % value to get the mean estimation value

print(f'value at {resample_line[inspection_value_idx]}% fitting everything: {mean_everything_curve[inspection_value_idx]}')
print(f'value at {resample_line[inspection_value_idx]}% fitting only complete measurements: {mean_nocensor_curve[inspection_value_idx]}')
print(f'value at {resample_line[inspection_value_idx]}% fitting everything with survival: {mean_censoring_curve[inspection_value_idx]}')

# fig, ax = plt.subplots()
#
#
# mean_of_means_everything = np.mean(iter_mean_everything_list, axis=0)
# mean_of_means_nocensor = np.mean(iter_mean_nocensor_list, axis=0)
# mean_of_means_censor = np.mean(iter_mean_censor_list, axis=0)
# mean_of_percentage = np.mean(iter_percentage_censoring_list, axis=0)
#
# print(np.std(iter_mean_censor_list))
#
# # print(iter_percentage_censoring_list)
# # print(mean_of_percentage)
#
#
# for i in range(n_iterations):
#     if i == 0:
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_everything_list[i], color='r', alpha=0.2, label='Fit all the data')
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_nocensor_list[i], color='b', alpha=0.2, label='Fit only complete data')
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_censor_list[i], color='g', alpha=0.2, label='Fit using survival')
#     else:
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_everything_list[i], color='r', alpha=0.2)
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_nocensor_list[i], color='b', alpha=0.2)
#         ax.plot(iter_percentage_censoring_list[i], iter_mean_censor_list[i], color='g', alpha=0.2)
#
#
# # ax.plot(mean_of_percentage, mean_of_means_everything, color='r', label='Fit all the data')
# # ax.plot(mean_of_percentage, mean_of_means_nocensor, color='b', label='Fit only complete data')
# # ax.plot(mean_of_percentage, mean_of_means_censor, color='g', label='Fit using survival')
#
# # ax.hlines(y=mean, xmin=0, xmax=100,
# #            colors='k', label='True mean')
# # ax.fill_between(mean_of_percentage, mean-std, mean+std, alpha=0.2)
#
ax.set_xlabel('% censored')
ax.set_ylabel('Estimated mean - Sample mean')
ax.set_ylim([-(mean+std+3), mean+std+3])
ax.legend()
plt.suptitle('Survival analysis estimation performance')
plt.title(f'{n_lines} data points drawn from lognormal ({mean}, {std}). {n_iterations} iterations')
plt.savefig(f'images/{mean}_{std}.png', dpi=200)
plt.show()

# sns.histplot(mean_censoring_curve.flatten())
# plt.show()
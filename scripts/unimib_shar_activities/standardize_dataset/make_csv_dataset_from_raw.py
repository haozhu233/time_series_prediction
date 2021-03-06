'''

Notes
-----
Uses the 9 "daily living" activities subset

In the 2017 paper, the activities are listed in Table 2 as
StandingUpFL    stand up from lying down position
LyingDownFS     lying down from seated position
StandingUpFS    stand up from seated position
Running         running forward at "normal" pace
SittingDown     sitting down from standing position
GoingDownS      going down stairs
GoingUpS        going up stairs
Walking         walking forward at "normal" pace
jumping         jumping (in place??)

But in the provided zip file, these are listed (in alphabetical order) as
'getting_up',
'going_down',
'going_up',
'jumping',
'lying_down',
'running',
'sitting_down',
'standing_up',
'walking'

Most are easy to match up, but to disambiguate getting_up and standing_up,
we looked at Figure 4 of the 2017 paper, which says
StandingUpFL has about 210 examples
StandingUpFS has about 160 examples

If we look at the raw data, we see
getting_up     216
standing_up    153

So getting up must be StandingUpFL, and standing up must be StandingUpFS

'''
import argparse
import numpy as np
import os
import pandas as pd
from scipy.io import loadmat

RAW_CATEGORY_NAMES = [
    'getting_up',
    'going_down',
    'going_up',
    'jumping',
    'lying_down',
    'running',
    'sitting_down',
    'standing_up',
    'walking']

NEW_CATEGORY_NAME_MAP = dict(
    going_up='UpStairs',
    going_down='DownStairs',
    getting_up='StandFromLie',
    standing_up='StandFromSit',
    jumping='Jump',
    walking='Walk',
    running='Run',
    lying_down='LieDown',
    sitting_down='SitDown',
    )

HORIZONTAL_MOTION_CATEGORY_NAMES = ['Walk', 'Run', 'UpStairs', 'DownStairs']

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dataset_path',
        default=None,
        help='Path to the data/ folder of unimib_shar_activities raw dataset')
    parser.add_argument(
        '--output_sensors_ts_csv_path',
        default=None,
        help='Path to csv file for tidy time-series of accelerometer sensor data')
    parser.add_argument(
        '--output_metadata_for_each_ts_csv_path',
        default=None,
        help='Path to csv file for per-sequence metadata (category, etc)')
    parser.add_argument(
        '--output_metadata_for_each_subj_csv_path',
        default=None,
        help='Path to csv file for per-subject metadata (age, weight, etc)')
    args = parser.parse_args()
    locals().update(args.__dict__)

    ## Verify correct dataset path
    if dataset_path is None:
        repo_dir = None
        if 'PROJECT_REPO_DIR' in os.environ:
            repo_dir = os.environ['PROJECT_REPO_DIR']
        else:
            repo_dir = os.path.abspath('../../../')

        if not os.path.exists(repo_dir):
            raise ValueError("Bad path to PROJECT_REPO_DIR:\n" + repo_dir)
        dataset_path = os.path.join(repo_dir, 'datasets', 'unimib_shar_activities/raw/', 'data')

    if not os.path.exists(dataset_path):
        raise ValueError("Bad path to raw data:\n" + dataset_path)

    ## Load the subject demographic data from .mat files

    full_data_mat_path = os.path.join(dataset_path, 'full_data.mat')
    full_data = loadmat(full_data_mat_path)['full_data']
    ages_per_subj = np.squeeze(np.asarray(
        [full_data[ii][2][0,0] for ii in range(30)], dtype=np.float32))
    height_cm_per_subj = np.squeeze(np.asarray(
        [full_data[ii][3][0,0] for ii in range(30)], dtype=np.float32))
    weight_kg_per_subj = np.squeeze(np.asarray(
        [full_data[ii][4][0,0] for ii in range(30)], dtype=np.float32))
    gender_str_per_subj = [str(full_data[ii][1][0]).strip() for ii in range(30)]
    is_male_per_subj = [0 if gstr == 'F' else 1 for gstr in gender_str_per_subj]
    subj_dem_df = pd.DataFrame(
        np.vstack([
            ages_per_subj, height_cm_per_subj, weight_kg_per_subj,
            is_male_per_subj, gender_str_per_subj]).T,
        columns=['age_yr', 'height_cm', 'weight_kg', 'is_male', 'gender_name'])
    subj_dem_df['subject_id'] = np.arange(1, 31, dtype=np.int32)
    subj_dem_df.to_csv(
        output_metadata_for_each_subj_csv_path,
        columns=['subject_id', 'age_yr', 'height_cm', 'weight_kg', 'is_male'],
        index=False)

    ## Load Accelerometer data
    # 2D array, n sequences x (3-channels x n_timesteps)
    adl_data_mat_path = os.path.join(dataset_path, 'adl_data.mat')
    adl_data = loadmat(adl_data_mat_path)['adl_data']

    labels_path = os.path.join(dataset_path, 'adl_labels.mat')
    meta_data = loadmat(labels_path)
    y_df = pd.DataFrame(meta_data['adl_labels'], columns=['raw_cat_id', 'subject_id', 'pocket_id'])
    n_seq = y_df.shape[0]
    y_df['subject_id'] = y_df['subject_id'].astype(np.int32)
    # Pockets should be binary, {0,1} encoding for {left, right}
    y_df['pocket_id'] = y_df['pocket_id'].astype(np.int32) - 1
    # Category ids should be in {0, 1, ... 8}
    y_df['category_id'] = y_df['raw_cat_id'].astype(np.int32) - 1
    y_df['sequence_id'] = np.arange(n_seq)

    names_path = os.path.join(dataset_path, 'adl_names.mat')
    label_names = [str(np.squeeze(u))
        for u in np.squeeze(loadmat(names_path)['adl_names'])]
    y_df['category_name'] = [
        NEW_CATEGORY_NAME_MAP.get(label_names[ii], label_names[ii])
        for ii in y_df['category_id']]
    y_df['horizontal_motion_binary_label'] = np.asarray([
        NEW_CATEGORY_NAME_MAP.get(label_names[ii], label_names[ii]) in HORIZONTAL_MOTION_CATEGORY_NAMES
        for ii in y_df['category_id']], dtype=np.int32)
    y_df.to_csv(output_metadata_for_each_ts_csv_path,
        columns=['subject_id', 'sequence_id', 'pocket_id', 'horizontal_motion_binary_label', 'category_name'],
        index=False)

    print("")
    print("subject_id | counts")
    print("-------------------")
    print(y_df['subject_id'].value_counts()[:5].sort_values(ascending=False).to_string(header=False))    
    print("...")
    print(y_df['subject_id'].value_counts()[-5:].sort_values(ascending=False).to_string(header=False))    
    

    print("")
    print("category_name | counts")
    print("----------------------")
    print(y_df['category_name'].value_counts()[:15].sort_values(ascending=False).to_string(header=False))    
    print("")
    print("pocket_id | counts")
    print("-------------------")
    print(y_df['pocket_id'].value_counts()[:15].sort_values(ascending=False).to_string(header=False))    
    

    # Unpack data into tidy time-series
    xyz_ts_arr_per_seq = list()
    seqid_ts_arr_per_seq = list()
    for seq_id, data_row in enumerate(adl_data):
        xyz_T3 = np.stack([data_row[:151], data_row[151:302], data_row[302:]]).T
        T = xyz_T3.shape[0]
        xyz_ts_arr_per_seq.append(xyz_T3)
        seqid_ts_arr_per_seq.append(seq_id * np.ones(T, dtype=np.int32))
    
    x_df = pd.DataFrame(np.vstack(xyz_ts_arr_per_seq), columns=['acc_x', 'acc_y', 'acc_z'])
    x_df['sequence_id'] = np.hstack(seqid_ts_arr_per_seq)
    x_df['timestep'] = np.hstack([np.arange(idvec.size) for idvec in seqid_ts_arr_per_seq])
    x_df = x_df.merge(y_df[['sequence_id', 'subject_id']], how='inner', on='sequence_id')
    x_df.to_csv(output_sensors_ts_csv_path,
        columns=['subject_id', 'sequence_id', 'timestep', 'acc_x', 'acc_y', 'acc_z'],
        index=False)


    '''
    ## HERE LIES OLD CODE FROM GABE

    xyz_data_per_seq = []
    ids_per_seq = []
    meta_per_seq = []
    seq_uid = 0
    for label_id, (d, i) in enumerate(zip(full_data_per_cat, ids_per_cat)):
        for di in d:
            xyz_T3 = np.stack([di[:151], di[151:302], di[302:]]).T
            xyz_data_per_seq.append(xyz_T3)
            T = xyz_T3.shape[0]
            ids_per_seq.append(seq_uid * np.ones(T, dtype=np.int32))
            seq_uid += 1
        tids = np.zeros(d.shape[0])
        for split, sids in enumerate(i):
            tids[sids - 1] = split
        meta_per_seq += [{
            'cvfold_id': sid,
            'category_name':label_names[label_id],
            'category_id': label_id} for sid in tids]

    # split_meta_per_cat : list of 2D arrays
    #   each entry is a n_folds x n_examples array
    split_info_path = os.path.join(dataset_path, 'split/split151/adl_test_idxssubjective_folds.mat')
    split_info_by_subj = loadmat(split_info_path)['test_idxs']

    # ids_per_cat : list of 2D arrays
    #   each entry is a n_folds x n_examples array
    ids_path = os.path.join(dataset_path, 'split/split151/adl_test_idxs5_folds.mat')
    ids_per_cat = np.squeeze(loadmat(ids_path)['test_idxs']).copy().tolist()
    '''

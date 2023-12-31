import time
import numpy as np
from scipy.sparse import csr_matrix, hstack
import pandas as pd
import scipy.sparse as sp
from collections import defaultdict
from sklearn.metrics.pairwise import cosine_similarity as cosine


class Dataset():
    def __init__(self, dataset, sep='\t', header_name=['u', 'i', 'r', 't', 'm'], pos_type=[4.0, 5.0], num_his_month=6,
                 num_cur_month=1, genre=19):
        self.pos_type = pos_type
        self.num_his_month = num_his_month
        self.num_cur_month = num_cur_month
        self.genre = genre
        self.data_path = 'dataset/{}'.format(dataset)
        self.data_frame = pd.read_csv('{}/ratings.csv'.format(self.data_path), sep=sep, header=None, names=header_name,
                                      engine='python')
        self.data_frame = self.data_frame.sort_values(by=['t'], ascending=True).reset_index(drop=True)
        self.start_time = min(self.data_frame['t'].unique())
        self.end_time = max(self.data_frame['t'].unique())
        #######################
        # Note: If you use your own dataset, you should use the following code to generate another coloum called 'm'
        #       in ```self.datas_frame```.
        #######################
        # self.data_frame.insert(len(header_name), 'm', 0)
        # for ind in range(self.data_frame.shape[0]):
        #     timestamp=self.data_frame['t'][ind]
        #     month = self.get_date_from_timestamp(timestamp)
        #     self.data_frame['m'][ind] = month
        self.month_list = list(self.data_frame['m'].unique())
        self.his_month_list = [i for i in range(0, 0 + num_his_month)]
        self.cur_month_list = [i for i in range(num_his_month, num_his_month + num_cur_month)]
        self.train_month_list = [i for i in range(0, num_his_month + num_cur_month)]
        self.test_month_set = list(set(self.month_list).difference(set(self.train_month_list)))
        self.data_frame_u = np.loadtxt('{}/user_feat.csv'.format(self.data_path), delimiter=' ')
        self.data_frame_i = np.loadtxt('{}/item_feat.csv'.format(self.data_path), delimiter=' ')
        self.num_user = self.data_frame_u.shape[0]
        self.num_item = self.data_frame_i.shape[0]

    def get_init_mats(self):
        init_adj_mat = np.zeros((self.num_user, self.num_item))
        init_time_mat = np.zeros((self.num_user, self.num_item))
        self.sub_data_frame = self.data_frame[self.data_frame['m'].isin(self.his_month_list)].reset_index(drop=True)
        print('# historical records: {}'.format(self.sub_data_frame.shape[0]), end='')
        for ind in range(self.sub_data_frame.shape[0]):
            u, i, r, t = self.sub_data_frame['u'][ind], self.sub_data_frame['i'][ind], self.sub_data_frame['r'][ind], \
                         self.sub_data_frame['t'][ind]
            init_adj_mat[u][i] = r
            init_time_mat[u][i] = t
        init_adj_mat = sp.csr_matrix(init_adj_mat)
        init_time_mat = sp.csr_matrix(init_time_mat)
        return init_adj_mat, init_time_mat

    @property
    def get_train_test_data(self):
        global adj_mat
        adj_mat = np.zeros((self.num_user, self.num_item))
        time_mat = np.zeros((self.num_user, self.num_item))
        self.sub_data_frame = self.data_frame[self.data_frame['m'].isin(self.cur_month_list)].reset_index(
            drop=True)
        print('\t# current records: {}'.format(self.sub_data_frame.shape[0]), end='')
        for ind in range(self.sub_data_frame.shape[0]):
            u, i, r, t = self.sub_data_frame['u'][ind], self.sub_data_frame['i'][ind], self.sub_data_frame['r'][ind], \
                         self.sub_data_frame['t'][ind]
            adj_mat[u][i] = r
            time_mat[u][i] = t
        cur_time = 1 / 2 * (max(list(self.sub_data_frame['t'].unique())) + min(
            list(self.sub_data_frame['t'].unique())))

        user_interacted_items_dict = defaultdict(list)
        test_user_items_dict = defaultdict(list)
        global his_user_interacted_items_dict
        his_user_interacted_items_dict = defaultdict(list)
        self.data_frame_train = self.data_frame[self.data_frame['m'].isin(self.train_month_list)].reset_index(drop=True)
        self.data_frame_his = self.data_frame_train[self.data_frame_train['m'].isin(self.his_month_list)].reset_index(
            drop=True)
        print('\t# records in training phase: {}'.format(self.data_frame_train.shape[0]), end='')
        self.data_frame_test = self.data_frame[self.data_frame['m'].isin(self.test_month_set)].reset_index(
            drop=True)
        print('\t# records in test phase: {}'.format(self.data_frame_test.shape[0]))
        for ind_train in range(self.data_frame_train.shape[0]):
            u, i = self.data_frame_train['u'][ind_train], self.data_frame_train['i'][ind_train]
            user_interacted_items_dict[u].append(i)
        for ind in range(self.data_frame_his.shape[0]):
            u, i = self.data_frame_train['u'][ind], self.data_frame_train['i'][ind]
            his_user_interacted_items_dict[u].append(i)
        for ind_test in range(self.data_frame_test.shape[0]):
            u, i, r = self.data_frame_test['u'][ind_test], self.data_frame_test['i'][ind_test], \
                      self.data_frame_test['r'][ind_test]
            if r in self.pos_type:
                test_user_items_dict[u].append(i)
        adj_mat = sp.csr_matrix(adj_mat)
        time_mat = sp.csr_matrix(time_mat)

        return adj_mat, time_mat, cur_time, user_interacted_items_dict, test_user_items_dict

    def get_uesr_sim_mat(self):
        matrix1 = []
        matrix2 = []
        for row_index in range(adj_mat.shape[0]):
            if row_index in his_user_interacted_items_dict:
                col_indices = adj_mat.indices[adj_mat.indptr[row_index]:adj_mat.indptr[row_index + 1]]
                values = adj_mat.data[adj_mat.indptr[row_index]:adj_mat.indptr[row_index + 1]]
                for col_index, value in zip(col_indices, values):
                    if col_index not in his_user_interacted_items_dict[row_index]:
                        matrix1.append([row_index, col_index, value])
            else:
                col_indices = adj_mat.indices[adj_mat.indptr[row_index]:adj_mat.indptr[row_index + 1]]
                values = adj_mat.data[adj_mat.indptr[row_index]:adj_mat.indptr[row_index + 1]]
                for col_index, value in zip(col_indices, values):
                    if col_index not in his_user_interacted_items_dict.get(row_index, []):
                        matrix2.append([row_index, col_index, value])

        rows, cols, data = zip(*matrix1)
        matrix1 = csr_matrix((data, (rows, cols)))
        rows, cols, data = zip(*matrix2)
        matrix2 = csr_matrix((data, (rows, cols)))
        if matrix1.shape[1] > matrix2.shape[1]:
            matrix2 = hstack([matrix2, csr_matrix((matrix2.shape[0], matrix1.shape[1] - matrix2.shape[1]))])
        else:
            matrix1 = hstack([matrix1, csr_matrix((matrix1.shape[0], matrix2.shape[1] - matrix1.shape[1]))])

        his_cur_user_sim_mat = matrix1.dot(matrix2.transpose())
        rowsum = np.array(his_cur_user_sim_mat.sum(axis=1))
        d_inv = np.power(rowsum, -0.5).flatten()
        d_inv[np.isinf(d_inv)] = 0.
        d_mat = sp.diags(d_inv, 0)
        norm_user_mat = d_mat.dot(his_cur_user_sim_mat)
        colsum = np.array(his_cur_user_sim_mat.sum(axis=0))
        d_inv = np.power(colsum, -0.5).flatten()
        d_inv[np.isinf(d_inv)] = 0.
        d_mat = sp.diags(d_inv)
        norm_user_mat = norm_user_mat.dot(d_mat)
        user_mat = norm_user_mat.copy()

        for i in range(norm_user_mat.shape[0]):
            max_index = np.argmax(norm_user_mat[i])
            user_mat[i, :max_index] = 0
            user_mat[i, max_index + 1:] = 0
        return user_mat

    def get_user_item_sim_mat(self, use_user_si, user_threshold, use_item_si, item_threshold):
        user_sim_mat = None
        item_sim_mat = None

        user_mat = self.get_uesr_sim_mat()
        siu_matrix = self.data_frame_u
        siu_mat = np.copy(siu_matrix)
        decay_factor_mat = np.zeros((self.num_user, 1))
        rows, cols = user_mat.nonzero()
        for i in range(len(rows)):
            row_index = rows[i]
            col_index = cols[i]
            data1 = siu_matrix[row_index, -self.genre:].tolist()
            data2 = siu_matrix[col_index, -self.genre:].tolist()
            or_result = [x or y for x, y in zip(data1, data2)]
            siu_matrix[row_index, -self.genre:] = or_result
        sii_matrix = self.data_frame_i
        if use_user_si:
            user_sim_mat = self.get_sim_mat(siu_matrix, user_threshold)
        if use_item_si:
            item_sim_mat = self.get_sim_mat(sii_matrix, item_threshold)
        n = siu_matrix.shape[1]
        for i in range(self.num_user):
            count = 0
            for j in range(n):
                if siu_matrix[i][j] != siu_mat[i][j]:
                    count += 1
            decay_factor_mat[i][0] = count
        decay_factor_mat = (np.exp(decay_factor_mat / self.genre)+np.exp(-decay_factor_mat / self.genre))/2
        return user_sim_mat, item_sim_mat, decay_factor_mat

    def get_sim_mat(self, si_matrix, beta, ):
        sim_mat = cosine(si_matrix)
        sim_mat[sim_mat < beta] = 0
        sim_mat = sp.csr_matrix(sim_mat)
        return sim_mat

    def get_date_from_timestamp(self, timestamp, mode='m'):
        time_array = time.localtime(timestamp)
        base_time_array = time.localtime(self.start_time)
        if mode == 'm':
            diff = time_array.tm_year - base_time_array.tm_year
            result = 12 * diff + time_array.tm_mon - base_time_array.tm_mon
        elif mode == 'y':  # For datasets with a period of one year (e.g. Douban Movie)
            result = time_array.tm_year - base_time_array.tm_year
        return result

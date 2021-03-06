from __future__ import division
import os
import re
import csv
import collections
import numpy as np
import tensorflow as tf
from tensorflow.contrib import learn
from tensorflow.python.ops import rnn, rnn_cell
import pdb
import pandas as pd



verbose = False
display_status_iter = 20 # To display training accuracy at regular intervals
shuffle_data = True # Indicates if the input data should be shuffled or not

# RNN Model Parameters
rnn_cell_size = 128 # hidden layer num of features (RNN hidden layer config size. Start with 128)
rnn_data_classes = 2 
rnn_data_embedding_size = 128 # Dimensionality of character embedding
rnn_data_vec_size = rnn_data_embedding_size
rnn_lstm_forget_bias = 1.0
rnn_dropout_keep_prob = 0.5
rnn_learning_rate = 0.001
rnn_num_epochs = 3
batch_size = 128

def process_str(string):
    string = string.strip().lower()
    string = re.sub(r"[^A-Za-z0-9(),!?\'\`]", " ", string)
    string = re.sub(r"\'s", " \'s", string)
    string = re.sub(r"\'ve", " \'ve", string)
    string = re.sub(r"n\'t", " n\'t", string)
    string = re.sub(r"\'re", " \'re", string)
    string = re.sub(r"\'d", " \'d", string)
    string = re.sub(r"\'ll", " \'ll", string)
    string = re.sub(r",", " , ", string)
    string = re.sub(r"!", " ! ", string)
    string = re.sub(r"\(", " \( ", string)
    string = re.sub(r"\)", " \) ", string)
    string = re.sub(r"\?", " \? ", string)
    string = re.sub(r"\s{2,}", " ", string)
    return string

def rnn_lstm(weights, biases, data_x, sequence_length, vocab_size, embedding_size):
	# Use Tensor Flow embedding lookup and convert the input data set
	with tf.device("/cpu:0"):
		embedding = tf.get_variable("embedding", [vocab_size, embedding_size])
		embedded_data = tf.nn.embedding_lookup(embedding, data_x)
		embedded_data_dropout = tf.nn.dropout(embedded_data, rnn_dropout_keep_prob)

	#add LSTM cell and dropout nodes
	rnn_lstm_cell = tf.nn.rnn_cell.BasicLSTMCell(rnn_cell_size, forget_bias = rnn_lstm_forget_bias)
	rnn_lstm_cell = tf.nn.rnn_cell.DropoutWrapper(rnn_lstm_cell, output_keep_prob = rnn_dropout_keep_prob)

	if verbose:
		print ("RNN rnn_data_X: ", embedded_data_dropout)

	rnn_data_X = embedded_data_dropout
	# Permuting batch_size and sequence_length
	rnn_data_X = tf.transpose(rnn_data_X, [1, 0, 2])
	#print ("RNN After transpose rnn_data_X: ", rnn_data_X)
	# Reshaping to (sequence_length * batch_size, rnn_data_vec_size)
	rnn_data_X = tf.reshape(rnn_data_X, [-1, rnn_data_vec_size])
	#print ("RNN After reshape rnn_data_X: ", rnn_data_X)
	# Split to get a list of 'sequence_length' tensors of shape (batch_size, rnn_data_vec_size)
	rnn_data_X = tf.split(rnn_data_X, sequence_length, 0)
	#print ("RNN After split len(rnn_data_X): ", len(rnn_data_X), rnn_data_X[0])

	# Get lstm cell output
	outputs, states = tf.nn.static_rnn(rnn_lstm_cell, rnn_data_X, dtype=tf.float32)

	output = tf.matmul(outputs[-1], weights) + biases
	return output

if __name__ == "__main__":
	

	DT = [0 , 1]
	HC = [1 , 0]
	

	#twitter_data_file = "../Data/train.csv"
	#twitter_test_file = "../Data/test.csv"

	print ("Started reading training dataset")
	# Reads data file. Gets X and Y dataset for analysis
	#twitter_data_cvs = open(twitter_data_file, 'r')
	#twitter_data_cvsreader = csv.reader(twitter_data_cvs)
	#twitter_data_cvsreader.next()

	#twitter_test_cvs = open(twitter_test_file, 'r')
	#twitter_test_cvsreader = csv.reader(twitter_test_cvs)
	#twitter_test_cvsreader.next()
	# Loop through file and process string
	X_data = []
	Y_data = []
	X_test = []
	
	max_document_length = 0
	invalid_row_count = 0
	with open("../Data/train.csv") as file:
		reader=csv.reader(file)
		next(reader)
		for row in reader:
		
			if row[0]=='HillaryClinton':

				sentiment_value = 1
			else:
				sentiment_value = 0
			sentment_text = process_str(row[1])
			max_document_length = max(max_document_length, len(sentment_text.split(" ")))

			if sentiment_value == 0:
				X_data.append(sentment_text)
				Y_data.append(DT)
			elif sentiment_value == 1:
				X_data.append(sentment_text)
				Y_data.append(HC)
			else:
				invalid_row_count += 1 
			#Invalid value. do not consider this row data
	#twitter_data_cvs.close()

	#max_document_length1=0
	with open("../Data/test.csv") as file:
		reader=csv.reader(file)
		next(reader)
		for row in reader:
		
			sentment_text = process_str(row[1])
			max_document_length = max(max_document_length, len(sentment_text.split(" ")))
			X_test.append(sentment_text)
			
	#twitter_test_cvs.close()
	# Convert list to np format for analysis
	
	Y_np_data = np.array(Y_data)
	
	data_size = len(Y_data)

	print ("Finished reading training dataset")
	#if invalid_row_count > 0:
	#	print ("Invalid Row Count : " + str(invalid_row_count))
	#print ("X_Y_Data Length : " + str(data_size))

	# Build vocabulary and convert the words to int
	vocab_processor = learn.preprocessing.VocabularyProcessor(max_document_length)
	X_np_data = np.array(list(vocab_processor.fit_transform(X_data)))
	X_np_test = np.array(list(vocab_processor.transform(X_test)))
	vocab_size = len(vocab_processor.vocabulary_)

	#print ("Vocabulary Size : " + str(vocab_size))
	#print ("Max Document Length : " + str(max_document_length))

	# Placeholders for input, output and dropout
	input_x = tf.placeholder(tf.int32, [None, max_document_length], name="input_x") # Place holder size format [rows, columns].
	input_y = tf.placeholder(tf.float32, [None, rnn_data_classes], name="input_y") # one column.

	# Define weights and biases for linear activation, using rnn inner loop last output
	weights = tf.Variable(tf.random_normal([rnn_cell_size, rnn_data_classes]))
	biases = tf.Variable(tf.random_normal([rnn_data_classes]))

	# For debugging
	if verbose:
		print ("Weights Shape: [", rnn_cell_size, rnn_data_classes, "], Biases Shape:[",rnn_data_classes,"]")
		print ("input_x : ", input_x)
		print ("input_y : ", input_y)

	# Define RNN LSTM cell ops
	sequence_length = max_document_length # (Time) Sequence length for RNN. In this case, it is maximum document text length
	prediction = rnn_lstm(weights, biases, input_x, sequence_length, vocab_size, rnn_data_embedding_size)

	# Define loss and optimizer
	cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=prediction,labels=input_y))
	optimizer = tf.train.AdamOptimizer(learning_rate=rnn_learning_rate).minimize(cost)

	# Evaluate model
	correct_prediction = tf.equal(tf.argmax(prediction,1), tf.argmax(input_y,1))
	accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

	# Initializing the variables
	init = tf.initialize_all_variables()

	# Launch the graph
	with tf.Session() as sess:
		sess.run(init)
		
		num_batches_per_epoch = int(data_size/batch_size) + 1
		total_iters = rnn_num_epochs * num_batches_per_epoch
		iter_num = 1

		print ("Started analysis... batch size : " + str(batch_size) + " batches per epoch : " + str(num_batches_per_epoch))
		print ("RNN cell size : " + str(rnn_cell_size) + " LSTM forget bias : " + str(rnn_lstm_forget_bias) + " Dropout keep probability : " + str(rnn_dropout_keep_prob))

		for epoch in range(rnn_num_epochs):
			total_acc=0
			# Shuffle the data at each epoch
			if shuffle_data:
				shuffle_indices = np.random.permutation(np.arange(data_size))
				shuffled_data_X = X_np_data[shuffle_indices]
				shuffled_data_Y = Y_np_data[shuffle_indices]
			else:
				shuffled_data_X = X_np_data
				shuffled_data_Y = Y_np_data

			for batch_num in range(num_batches_per_epoch):
				start_index = batch_num * batch_size
				end_index = min((batch_num + 1) * batch_size, data_size)
				# X training and Y training datasets
				X_train = shuffled_data_X[start_index:end_index]
				Y_train = shuffled_data_Y[start_index:end_index]

				sess.run(optimizer, feed_dict = { input_x: X_train, input_y: Y_train})

				if iter_num % display_status_iter == 0:
					# Display at regulat intervals.
					# Calculate batch accuracy
					acc = sess.run(accuracy, feed_dict={input_x: X_train, input_y: Y_train})
					# Calculate batch loss
					loss = sess.run(cost, feed_dict={input_x: X_train, input_y: Y_train})
					print ("Iter " + str(iter_num) + " of " + str(total_iters) + ", Batch Loss= " + \
					"{:.6f}".format(loss) + ", Training Accuracy= " + \
					"{:.5f}".format(acc))
					#total_acc = total_acc + acc
				iter_num += 1
		#print ((total_acc / total_iters)*100)
				#print "Testing Accuracy:", \
		
		results1=sess.run(tf.nn.softmax(prediction),feed_dict={input_x: X_np_data,input_y:Y_np_data})
		print(results1)

		results=sess.run(tf.nn.softmax(prediction),feed_dict={input_x: X_np_test})
		df = pd.DataFrame(data=results,columns=['HillaryClinton','realDonaldTrump'])
		df.index.name='id'
		df.to_csv("output.csv")
		#print (results.type())






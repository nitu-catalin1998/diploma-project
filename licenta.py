# -*- coding: utf-8 -*-
"""Licenta.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1euRBkCo0SrLUyAZVQrKf4HiD07BaZCgP

# Intelligent Linguistic System for the Grammar of the Romanian Language

## Authors:

* Conf. Dr. Ing. Rebedea Traian-Eugen (Scientific coordinator)
* Ing. Coteț Teodor-Mihai (Special thanks - Co-tutor)
* Nițu Ioan-Florin-Cătălin 342C4
"""

################################################################################
##                           _    _   _ __    _ __                            ##
##                          | |  | | | '_ \  | '_ \                           ##
##                          | |  | | | |_) | | |_) |                          ##
##                          | |  | | | .__/  | '_ )                           ##
##                          | \__/ | | |     | |_) |                          ##
##                          \______/ |_|     |_.__/                           ##
##                          -------- _______ -------                          ##
##                                                                            ##
################################################################################
##  File:           Licenta.ipynb                                             ##
##  Description:    Intelligent Linguistic System for Romanian Grammar        ##
##  By:             ioan_florin.nitu                                          ##
################################################################################
##  This program implements a program for the Romanian Language Grammar       ##
################################################################################
##  The program operates with Neural Networks:                                ##
##   - Datasets                                                               ##
##   - Attention                                                              ##
##   - Layers                                                                 ##
##   - Encoders and Decoders                                                  ##
##   - Transformers                                                           ##
##  Finished in 2 weeks of continue work!                                     ##
################################################################################
##   _______________________________________                                  ##
##  / Look for my W-USO ;)                  \                                 ##
##  \ (No, seriously, don't look...)        /                                 ##
##   ---------------------------------------                                  ##
##          \   ^__^                                                          ##
##           \  (oo)\_______                                                  ##
##              (__)\       )\/\                                              ##
##                  ||----w |                                                 ##
##                  ||     ||                                                 ##
##                                                                            ##
##                                                                            ##
################################################################################

### LICENTA
 #
 # Licenta.ipynb
 #
 # @author Nitu Ioan Florin Catalin
 # @group 342C4
 # @version 1
 # @since Rock 'n' Roll
 #
 # Copyright (c) 2020 ACS
 #
 ##

"LICENTA: Nitu Ioan-Florin-Catalin, 342C4, CTI, DC, FAC, UPB, 2020"

import tensorflow as tf
import tensorflow_datasets as tfds
from nltk.translate.bleu_score import SmoothingFunction, \
                                      sentence_bleu as bleu_score
import os
import time
import numpy as np
import matplotlib.pyplot as plt

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard

"""## Setup Input Pipeline"""

BUFFER_SIZE = 20000
BATCH_SIZE = 64
MAX_LENGTH = 512
EPOCHS = 100

"""### Dataset"""

def load_dataset(filename, directory="/content/drive/My Drive"):
    def spliter(example):
        sentences = tf.strings.split(example, sep='\t')
        (tar, inp) = (sentences[0], sentences[1])
        return (inp, tar)
    dataset = tf.data.TextLineDataset(os.path.join(directory, filename))
    splited_dataset = dataset.map(lambda example: spliter(example))
    return splited_dataset

#huge_examples = load_dataset("10_mil_dirty_clean_better.txt")
#huge_examples = load_dataset("1_mil_dirty_clean_better.txt")
#huge_examples = load_dataset("50_k_dirty_clean_better.txt")
train_examples = load_dataset("train.txt")
test_examples = load_dataset("test.txt")
eval_examples = load_dataset("dev.txt")
#train_examples = huge_examples.concatenate(train_examples)
tokenizer_inp = tfds.features.text.SubwordTextEncoder.build_from_corpus(
                    (inp.numpy() for (inp, tar) in train_examples),
                    target_vocab_size=2 ** 11)
tokenizer_tar = tfds.features.text.SubwordTextEncoder.build_from_corpus(
                    (tar.numpy() for (inp, tar) in train_examples),
                    target_vocab_size=2 ** 11)

def tf_encode(inp, tar):
    def encode(inp, tar):
        inp = [tokenizer_inp.vocab_size] + tokenizer_inp.encode(inp.numpy()) + \
                [tokenizer_inp.vocab_size + 1]
        tar = [tokenizer_tar.vocab_size] + tokenizer_tar.encode(tar.numpy()) + \
                [tokenizer_tar.vocab_size + 1]
        return (inp, tar)
    results = tf.py_function(encode, [inp, tar], [tf.int64, tf.int64])
    (result_inp, result_tar) = results
    result_inp.set_shape([None])
    result_tar.set_shape([None])
    return (result_inp, result_tar)

def filter_max_length(x, y, max_length=MAX_LENGTH):
    return tf.logical_and(tf.size(x) <= max_length, tf.size(y) <= max_length)

train_dataset = train_examples.map(tf_encode)
train_dataset = train_dataset.filter(filter_max_length)
# cache the dataset to memory to get a speedup while reading from it.
train_dataset = train_dataset.cache()
train_dataset = train_dataset.shuffle(BUFFER_SIZE).padded_batch(BATCH_SIZE)
train_dataset = train_dataset.prefetch(tf.data.experimental.AUTOTUNE)
eval_dataset = eval_examples.map(tf_encode)
eval_dataset = eval_dataset.filter(filter_max_length)
eval_dataset = eval_dataset.padded_batch(BATCH_SIZE)
test_dataset = test_examples.map(tf_encode)
test_dataset = test_dataset.filter(filter_max_length)
test_dataset = test_dataset.padded_batch(BATCH_SIZE)

"""### Masking"""

def create_padding_mask(seq):
    seq = tf.cast(tf.math.equal(seq, 0), tf.float32)
    # add extra dimensions to add the padding
    # to the attention logits.
    return seq[:, tf.newaxis, tf.newaxis, :]  # (batch_size, 1, 1, seq_len)

def create_look_ahead_mask(size):
    mask = 1 - tf.linalg.band_part(tf.ones((size, size)), -1, 0)
    return mask  # (seq_len, seq_len)

def create_masks(inp, tar):
    # Encoder padding mask
    enc_padding_mask = create_padding_mask(inp)
    # Used in the 2nd attention block in the decoder.
    # This padding mask is used to mask the encoder outputs.
    dec_padding_mask = create_padding_mask(inp)
    # Used in the 1st attention block in the decoder.
    # It is used to pad and mask future tokens in the input received by 
    # the decoder.
    look_ahead_mask = create_look_ahead_mask(tf.shape(tar)[1])
    dec_target_padding_mask = create_padding_mask(tar)
    combined_mask = tf.maximum(dec_target_padding_mask, look_ahead_mask)
    return enc_padding_mask, combined_mask, dec_padding_mask

"""## Attention

### Scaled Dot Product Attention
"""

def scaled_dot_product_attention(q, k, v, mask):
    """Calculate the attention weights.
    q, k, v must have matching leading dimensions.
    k, v must have matching penultimate dimension, i.e.: seq_len_k = seq_len_v.
    The mask has different shapes depending on its type(padding or look ahead)
    but it must be broadcastable for addition.

    Args:
    q: query shape == (..., seq_len_q, depth)
    k: key shape == (..., seq_len_k, depth)
    v: value shape == (..., seq_len_v, depth_v)
    mask: Float tensor with shape broadcastable 
            to (..., seq_len_q, seq_len_k). Defaults to None.

    Returns:
    output, attention_weights
    """
    matmul_qk = tf.matmul(q, k, transpose_b=True)  # (..., seq_len_q, seq_len_k)
    # scale matmul_qk
    dk = tf.cast(tf.shape(k)[-1], tf.float32)
    scaled_attention_logits = matmul_qk / tf.math.sqrt(dk)
    # add the mask to the scaled tensor.
    if mask is not None:
        scaled_attention_logits += (mask * -1e9)
    # softmax is normalized on the last axis (seq_len_k) so that the scores
    # add up to 1.
    attention_weights = tf.nn.softmax(scaled_attention_logits, axis=-1)
                        # (..., seq_len_q, seq_len_k)
    output = tf.matmul(attention_weights, v)  # (..., seq_len_q, depth_v)
    return output, attention_weights

"""### Multi-Head Attention"""

class MultiHeadAttention(tf.keras.layers.Layer):

    def __init__(self, d_model, num_heads):
        super(MultiHeadAttention, self).__init__()
        self.num_heads = num_heads
        self.d_model = d_model
        assert d_model % self.num_heads == 0
        self.depth = d_model // self.num_heads
        self.wq = tf.keras.layers.Dense(d_model)
        self.wk = tf.keras.layers.Dense(d_model)
        self.wv = tf.keras.layers.Dense(d_model)
        self.dense = tf.keras.layers.Dense(d_model)

    def split_heads(self, x, batch_size):
        """Split the last dimension into (num_heads, depth).
        Transpose the result such that the shape is
        (batch_size, num_heads, seq_len, depth)
        """
        x = tf.reshape(x, (batch_size, -1, self.num_heads, self.depth))
        return tf.transpose(x, perm=[0, 2, 1, 3])

    def call(self, v, k, q, mask):
        batch_size = tf.shape(q)[0]
        q = self.wq(q)  # (batch_size, seq_len, d_model)
        k = self.wk(k)  # (batch_size, seq_len, d_model)
        v = self.wv(v)  # (batch_size, seq_len, d_model)
        q = self.split_heads(q, batch_size)
            # (batch_size, num_heads, seq_len_q, depth)
        k = self.split_heads(k, batch_size)
            # (batch_size, num_heads, seq_len_k, depth)
        v = self.split_heads(v, batch_size)
            # (batch_size, num_heads, seq_len_v, depth)
        # scaled_attention.shape == (batch_size, num_heads, seq_len_q, depth)
        # attention_weights.shape == (batch_size, num_heads, seq_len_q,
        #                             seq_len_k)
        (scaled_attention, attention_weights) = scaled_dot_product_attention(q,
                                                                    k, v, mask)
        scaled_attention = tf.transpose(scaled_attention, perm=[0, 2, 1, 3])
                           # (batch_size, seq_len_q, num_heads, depth)
        concat_attention = tf.reshape(scaled_attention,
                                      (batch_size, -1, self.d_model))
                           # (batch_size, seq_len_q, d_model)
        output = self.dense(concat_attention)
                 # (batch_size, seq_len_q, d_model)
        return output, attention_weights

"""## Coder Layers

### Point Wise Feed Forward Network
"""

def point_wise_feed_forward_network(d_model, dff):
    return tf.keras.Sequential([
                                tf.keras.layers.Dense(dff, activation="relu"),
                                # (batch_size, seq_len, dff)
                                tf.keras.layers.Dense(d_model)
                                # (batch_size, seq_len, d_model)
                               ])

"""### Encoder Layer"""

class EncoderLayer(tf.keras.layers.Layer):

    def __init__(self, d_model, num_heads, dff, rate=0.1):
        super(EncoderLayer, self).__init__()
        self.mha = MultiHeadAttention(d_model, num_heads)
        self.ffn = point_wise_feed_forward_network(d_model, dff)
        self.layernorm1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = tf.keras.layers.Dropout(rate)
        self.dropout2 = tf.keras.layers.Dropout(rate)

    def call(self, x, training, mask):
        (attn_output, _) = self.mha(x, x, x, mask)
                           # (batch_size, input_seq_len, d_model)
        attn_output = self.dropout1(attn_output, training=training)
        out1 = self.layernorm1(x + attn_output)
               # (batch_size, input_seq_len, d_model)
        ffn_output = self.ffn(out1)  # (batch_size, input_seq_len, d_model)
        ffn_output = self.dropout2(ffn_output, training=training)
        out2 = self.layernorm2(out1 + ffn_output)
               # (batch_size, input_seq_len, d_model)
        return out2

"""### Decoder Layer"""

class DecoderLayer(tf.keras.layers.Layer):

    def __init__(self, d_model, num_heads, dff, rate=0.1):
        super(DecoderLayer, self).__init__()
        self.mha1 = MultiHeadAttention(d_model, num_heads)
        self.mha2 = MultiHeadAttention(d_model, num_heads)
        self.ffn = point_wise_feed_forward_network(d_model, dff)
        self.layernorm1 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.layernorm2 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.layernorm3 = tf.keras.layers.LayerNormalization(epsilon=1e-6)
        self.dropout1 = tf.keras.layers.Dropout(rate)
        self.dropout2 = tf.keras.layers.Dropout(rate)
        self.dropout3 = tf.keras.layers.Dropout(rate)

    def call(self, x, enc_output, training, look_ahead_mask, padding_mask):
        # enc_output.shape == (batch_size, input_seq_len, d_model)
        (attn1, attn_weights_block1) = self.mha1(x, x, x, look_ahead_mask)
                                       # (batch_size, target_seq_len, d_model)
        attn1 = self.dropout1(attn1, training=training)
        out1 = self.layernorm1(attn1 + x)
        (attn2, attn_weights_block2) = self.mha2(enc_output, enc_output, out1,
                                                 padding_mask)
                                       # (batch_size, target_seq_len, d_model)
        attn2 = self.dropout2(attn2, training=training)
        out2 = self.layernorm2(attn2 + out1)
               # (batch_size, target_seq_len, d_model)
        ffn_output = self.ffn(out2)  # (batch_size, target_seq_len, d_model)
        ffn_output = self.dropout3(ffn_output, training=training)
        out3 = self.layernorm3(ffn_output + out2)
               # (batch_size, target_seq_len, d_model)
        return out3, attn_weights_block1, attn_weights_block2

"""## Coder

### Positional Encoding
"""

def positional_encoding(position, d_model):
    def get_angles(pos, i, d_model):
        angle_rates = 1 / np.power(10000, (2 * (i // 2)) / np.float32(d_model))
        return pos * angle_rates
    angle_rads = get_angles(np.arange(position)[:, np.newaxis],
                            np.arange(d_model)[np.newaxis, :], d_model)
    # apply sin to even indices in the array; 2i
    angle_rads[:, 0::2] = np.sin(angle_rads[:, 0::2])
    # apply cos to odd indices in the array; 2i+1
    angle_rads[:, 1::2] = np.cos(angle_rads[:, 1::2])
    pos_encoding = angle_rads[np.newaxis, ...]
    return tf.cast(pos_encoding, dtype=tf.float32)

"""### Encoder"""

class Encoder(tf.keras.layers.Layer):

    def __init__(self, num_layers, d_model, num_heads, dff, input_vocab_size, 
                 maximum_position_encoding, rate=0.1):
        super(Encoder, self).__init__()
        self.d_model = d_model
        self.num_layers = num_layers
        self.embedding = tf.keras.layers.Embedding(input_vocab_size, d_model)
        self.pos_encoding = positional_encoding(maximum_position_encoding,
                                                d_model)
        self.enc_layers = [EncoderLayer(d_model, num_heads, dff, rate)
                           for _ in range(num_layers)]
        self.dropout = tf.keras.layers.Dropout(rate)

    def call(self, x, training, mask):
        seq_len = tf.shape(x)[1]
        # adding embedding and position encoding.
        x = self.embedding(x)  # (batch_size, input_seq_len, d_model)
        x *= tf.math.sqrt(tf.cast(self.d_model, tf.float32))
        x += self.pos_encoding[:, :seq_len, :]
        x = self.dropout(x, training=training)
        for i in range(self.num_layers):
            x = self.enc_layers[i](x, training, mask)
        return x  # (batch_size, input_seq_len, d_model)

"""### Decoder"""

class Decoder(tf.keras.layers.Layer):

    def __init__(self, num_layers, d_model, num_heads, dff, target_vocab_size,
                 maximum_position_encoding, rate=0.1):
        super(Decoder, self).__init__()
        self.d_model = d_model
        self.num_layers = num_layers
        self.embedding = tf.keras.layers.Embedding(target_vocab_size, d_model)
        self.pos_encoding = positional_encoding(maximum_position_encoding,
                                                d_model)
        self.dec_layers = [DecoderLayer(d_model, num_heads, dff, rate)
                           for _ in range(num_layers)]
        self.dropout = tf.keras.layers.Dropout(rate)

    def call(self, x, enc_output, training, look_ahead_mask, padding_mask):
        seq_len = tf.shape(x)[1]
        attention_weights = {}
        x = self.embedding(x)  # (batch_size, target_seq_len, d_model)
        x *= tf.math.sqrt(tf.cast(self.d_model, tf.float32))
        x += self.pos_encoding[:, :seq_len, :]
        x = self.dropout(x, training=training)
        for i in range(self.num_layers):
            x, block1, block2 = self.dec_layers[i](x, enc_output, training,
                                                   look_ahead_mask,
                                                   padding_mask)
            attention_weights["decoder_layer{}_block1".format(i + 1)] = block1
            attention_weights["decoder_layer{}_block2".format(i + 1)] = block2
        # x.shape == (batch_size, target_seq_len, d_model)
        return x, attention_weights

"""## Transformer"""

class Transformer(tf.keras.Model):

    def __init__(self, num_layers, d_model, num_heads, dff, input_vocab_size,
                 target_vocab_size, pe_input, pe_target, rate=0.1):
        super(Transformer, self).__init__()
        self.encoder = Encoder(num_layers, d_model, num_heads, dff,
                               input_vocab_size, pe_input, rate)
        self.decoder = Decoder(num_layers, d_model, num_heads, dff,
                               target_vocab_size, pe_target, rate)
        self.final_layer = tf.keras.layers.Dense(target_vocab_size)

    def call(self, inp, tar, training, enc_padding_mask, look_ahead_mask,
             dec_padding_mask):
        enc_output = self.encoder(inp, training, enc_padding_mask)
                     # (batch_size, inp_seq_len, d_model)
        # dec_output.shape == (batch_size, tar_seq_len, d_model)
        dec_output, attention_weights = self.decoder(tar, enc_output, training,
                                                     look_ahead_mask,
                                                     dec_padding_mask)
        final_output = self.final_layer(dec_output)
                       # (batch_size, tar_seq_len, target_vocab_size)
        return final_output, attention_weights

"""### Hyperparameters"""

# The values used in the base model of transformer were;
# num_layers = 6, d_model = 512, dff = 2048.
# See the paper for all the other versions of the transformer.
num_layers = 2
d_model = 128
dff = 128
num_heads = 2

input_vocab_size = tokenizer_inp.vocab_size + 2
target_vocab_size = tokenizer_tar.vocab_size + 2
dropout_rate = 0.1

"""## Optimizer"""

class CustomSchedule(tf.keras.optimizers.schedules.LearningRateSchedule):

    def __init__(self, d_model, warmup_steps=4000):
        super(CustomSchedule, self).__init__()
        self.d_model = d_model
        self.d_model = tf.cast(self.d_model, tf.float32)
        self.warmup_steps = warmup_steps

    def __call__(self, step):
        arg1 = tf.math.rsqrt(step)
        arg2 = step * (self.warmup_steps ** -1.5)
        return tf.math.rsqrt(self.d_model) * tf.math.minimum(arg1, arg2)

learning_rate = CustomSchedule(d_model)
optimizer = tf.keras.optimizers.Adam(learning_rate, beta_1=0.9, beta_2=0.98, 
                                     epsilon=1e-9)

"""## Loss and Metrics"""

loss_object = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True,
                                                            reduction="none")
def loss_function(real, pred):
    mask = tf.math.logical_not(tf.math.equal(real, 0))
    loss_ = loss_object(real, pred)
    mask = tf.cast(mask, dtype=loss_.dtype)
    loss_ *= mask
    return tf.reduce_sum(loss_) / tf.reduce_sum(mask)

train_loss = tf.keras.metrics.Mean(name="train_loss")
train_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(
                                                        name="train_accuracy")
test_loss = tf.keras.metrics.Mean(name="test_loss")
test_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(
                                                        name="test_accuracy")
eval_loss = tf.keras.metrics.Mean(name="eval_loss")
eval_accuracy = tf.keras.metrics.SparseCategoricalAccuracy(name="eval_accuracy")

"""## Training and Checkpointing"""

transformer = Transformer(num_layers, d_model, num_heads, dff, input_vocab_size,
                          target_vocab_size, pe_input=input_vocab_size, 
                          pe_target=target_vocab_size, rate=dropout_rate)

"""### Checkpointing"""

checkpoint_path = "./checkpoints/train"
ckpt = tf.train.Checkpoint(transformer=transformer, optimizer=optimizer)
ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=1)
# if a checkpoint exists, restore the latest checkpoint.
if ckpt_manager.latest_checkpoint:
    ckpt.restore(ckpt_manager.latest_checkpoint)
    print ("Latest checkpoint restored!!")

"""### Training"""

# Commented out IPython magic to ensure Python compatibility.
train_log_dir = 'logs/gradient_tape/train'
test_log_dir = 'logs/gradient_tape/test'
train_summary_writer = tf.summary.create_file_writer(train_log_dir)
test_summary_writer = tf.summary.create_file_writer(test_log_dir)
# %tensorboard --logdir logs/gradient_tape

# The @tf.function trace-compiles train_step into a TF graph for faster
# execution. The function specializes to the precise shape of the argument
# tensors. To avoid re-tracing due to the variable sequence lengths or variable
# batch sizes (the last batch is smaller), use input_signature to specify
# more generic shapes.

train_step_signature = [
                        tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                        tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                       ]

@tf.function(input_signature=train_step_signature)
def train_step(inp, tar):
    tar_inp = tar[:, :-1]
    tar_real = tar[:, 1:]
    (enc_padding_mask, combined_mask, dec_padding_mask) = create_masks(inp,
                                                                       tar_inp)
    with tf.GradientTape() as tape:
        (predictions, _) = transformer(inp, tar_inp, True, enc_padding_mask,
                                       combined_mask, dec_padding_mask)
        loss = loss_function(tar_real, predictions)
        gradients = tape.gradient(loss, transformer.trainable_variables)    
        optimizer.apply_gradients(zip(gradients,
                                      transformer.trainable_variables))
        train_loss(loss)
        train_accuracy(tar_real, predictions)

# The @tf.function trace-compiles train_step into a TF graph for faster
# execution. The function specializes to the precise shape of the argument
# tensors. To avoid re-tracing due to the variable sequence lengths or variable
# batch sizes (the last batch is smaller), use input_signature to specify
# more generic shapes.

test_step_signature = [
                       tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                       tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                      ]

@tf.function(input_signature=test_step_signature)
def test_step(inp, tar):
    tar_inp = tar[:, :-1]
    tar_real = tar[:, 1:]
    (enc_padding_mask, combined_mask, dec_padding_mask) = create_masks(inp,
                                                                       tar_inp)
    with tf.GradientTape() as tape:
        (predictions, _) = transformer(inp, tar_inp, False, enc_padding_mask,
                                       combined_mask, dec_padding_mask)
        loss = loss_function(tar_real, predictions)
        test_loss(loss)
        test_accuracy(tar_real, predictions)

for epoch in range(EPOCHS):
    start = time.time()
    train_loss.reset_states()
    train_accuracy.reset_states()
    test_loss.reset_states()
    test_accuracy.reset_states()
    # inp -> incorrect, tar -> correct
    for (batch, (inp, tar)) in enumerate(train_dataset):
        train_step(inp, tar)
        if batch % 50 == 0:
            print("Epoch {} Batch {} Loss {:.4f} Accuracy {:.4f}".format(
                    epoch + 1, batch, train_loss.result(),
                    train_accuracy.result()))
    with train_summary_writer.as_default():
        tf.summary.scalar('loss', train_loss.result(), step=epoch)
        tf.summary.scalar('accuracy', train_accuracy.result(), step=epoch)
    if (epoch + 1) % 5 == 0:
        ckpt_save_path = ckpt_manager.save()
        print("Saving checkpoint for epoch {} at {}".format(epoch + 1,
                                                            ckpt_save_path))
    print("Epoch {} Loss {:.4f} Accuracy {:.4f}".format(epoch + 1,
                                                        train_loss.result(),
                                                        train_accuracy.result())
    )
    for (batch, (inp, tar)) in enumerate(test_dataset):
        test_step(inp, tar)
        if batch % 50 == 0:
            print("Test {} Batch {} Loss {:.4f} Accuracy {:.4f}".format(
                    epoch + 1, batch, test_loss.result(),
                    test_accuracy.result()))
    with test_summary_writer.as_default():
        tf.summary.scalar('loss', test_loss.result(), step=epoch)
        tf.summary.scalar('accuracy', test_accuracy.result(), step=epoch)
    print("Test {} Loss {:.4f} Accuracy {:.4f}".format(epoch + 1,
                                                       test_loss.result(),
                                                       test_accuracy.result())
    )
    print("Time taken for 1 epoch: {} secs\n".format(time.time() - start))

"""## Evaluate"""

# The @tf.function trace-compiles eval_step into a TF graph for faster
# execution. The function specializes to the precise shape of the argument
# tensors. To avoid re-tracing due to the variable sequence lengths or variable
# batch sizes (the last batch is smaller), use input_signature to specify
# more generic shapes.

eval_step_signature = [
                       tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                       tf.TensorSpec(shape=(None, None), dtype=tf.int64),
                      ]

@tf.function(input_signature=eval_step_signature)
def eval_step(inp, tar):
    tar_inp = tar[:, :-1]
    tar_real = tar[:, 1:]
    (enc_padding_mask, combined_mask, dec_padding_mask) = create_masks(inp,
                                                                       tar_inp)
    with tf.GradientTape() as tape:
        (predictions, _) = transformer(inp, tar_inp, False, enc_padding_mask,
                                       combined_mask, dec_padding_mask)
        loss = loss_function(tar_real, predictions)
        eval_loss(loss)
        eval_accuracy(tar_real, predictions)

for epoch in range(1):
    start = time.time()
    eval_loss.reset_states()
    eval_accuracy.reset_states()
    # inp -> incorrect, tar -> correct
    for (batch, (inp, tar)) in enumerate(eval_dataset):
        eval_step(inp, tar)
        if batch % 50 == 0:
            print("Epoch {} Batch {} Loss {:.4f} Accuracy {:.4f}".format(
                    epoch, batch, eval_loss.result(),
                    eval_accuracy.result()))
    print("Epoch {} Loss {:.4f} Accuracy {:.4f}".format(epoch,
                                                        eval_loss.result(),
                                                        eval_accuracy.result())
    )
    print("Time taken for 1 epoch: {} secs\n".format(time.time() - start))

"""### Correction"""

def evaluate(inp_sentence):
    start_token = [tokenizer_inp.vocab_size]
    end_token = [tokenizer_inp.vocab_size + 1]
    # inp sentence is incorrect, hence adding the start and end token
    inp_sentence = start_token + tokenizer_inp.encode(inp_sentence) + end_token
    encoder_input = tf.expand_dims(inp_sentence, 0)
    # as the target is correct, the first word to the transformer should be the
    # correct start token.
    decoder_input = [tokenizer_tar.vocab_size]
    output = tf.expand_dims(decoder_input, 0)
    for i in range(MAX_LENGTH):
        (enc_padding_mask, combined_mask, dec_padding_mask) = create_masks(
                                                          encoder_input, output)
        # predictions.shape == (batch_size, seq_len, vocab_size)
        (predictions, attention_weights) = transformer(encoder_input, output,
                                                       False, enc_padding_mask,
                                                       combined_mask,
                                                       dec_padding_mask)
        # select the last word from the seq_len dimension
        predictions = predictions[: , -1:, :]  # (batch_size, 1, vocab_size)
        predicted_id = tf.cast(tf.argmax(predictions, axis=-1), tf.int32)
        # return the result if the predicted_id is equal to the end token
        if predicted_id == tokenizer_tar.vocab_size + 1:
            return tf.squeeze(output, axis=0), attention_weights
        # concatentate the predicted_id to the output which is given to the
        # decoder as its input.
        output = tf.concat([output, predicted_id], axis=-1)
    return tf.squeeze(output, axis=0), attention_weights

def plot_attention_weights(attention, sentence, result, layer):
    fig = plt.figure(figsize=(16, 8))
    sentence = tokenizer_inp.encode(sentence)
    attention = tf.squeeze(attention[layer], axis=0)
    for head in range(attention.shape[0]):
        ax = fig.add_subplot(2, 4, head+1)
        # plot the attention weights
        ax.matshow(attention[head][:-1, :], cmap="viridis")
        fontdict = {"fontsize": 10}
        ax.set_xticks(range(len(sentence) + 2))
        ax.set_yticks(range(len(result)))
        ax.set_ylim(len(result) - 1.5, -0.5)
        ax.set_xticklabels(["<start>"] + \
                           [tokenizer_inp.decode([i]) for i in sentence] + \
                           ["<end>"],
                           fontdict=fontdict, rotation=90)
        ax.set_yticklabels([tokenizer_tar.decode([i]) \
                            for i in result if i < tokenizer_tar.vocab_size],
                           fontdict=fontdict)
        ax.set_xlabel("Head {}".format(head + 1))
    plt.tight_layout()
    plt.show()

def correct(sentence, real_sentence=None, verbose=True, plot=""):
    score = None
    assert isinstance(sentence, str) == True
    (result, attention_weights) = evaluate(sentence)
    predicted_sentence = tokenizer_tar.decode([i
                                               for i in result
                                               if i < tokenizer_tar.vocab_size])
    if verbose:
        print("Input: {}".format(sentence))
        print("Predicted correction: {}".format(predicted_sentence))
    if not real_sentence is None:
        assert isinstance(real_sentence, str) == True
        try:
            score = bleu_score([real_sentence.split(' ')],
                               predicted_sentence.split(' '),
                               smoothing_function=SmoothingFunction().method4)
        except:
            score = 0
        if verbose:
            print("Real correction: {}".format(real_sentence))
            print("BLEU score: {:.4f}".format(score))
    if plot:
        plot_attention_weights(attention_weights, sentence, result, plot)
    return score

"""### Testing"""

correct("Alte mărci comerciale utilizate vreme îndelungată sunt Löwenbräu, deținătorii căreia spun că este folosită din 1383, și Stella Artois  din 1366.",
        real_sentence="Alte mărci comerciale utilizate vreme îndelungată sunt Löwenbräu, deținătorii căreia spun că este folosită din 1383, și Stella Artois  din 1366.",
        plot="decoder_layer2_block2")

correct("Cea mai importantă este ceea surprinsă asupra luni Noiembrie.",
        real_sentence="Cea mai importantă este cea surprinsă asupra lunii Noiembrie.",
        plot="decoder_layer2_block2")

correct("„Nici odată nam văzut cartea așa” a mărturisit el.",
        real_sentence="„Niciodată n-am văzut cartea așa”, a mărturisit el.",
        plot="decoder_layer2_block2")

correct("Incinta exterioară în partea de est, astăzi goală, deținea altă dată, donjonul construit pentru Filip al II-lea  în 1219, cu ocazia unei confiscări a senioriei, ca Catedrala Colegială Saint-Ythier, mutată de Maximilien De Béthune  în interiorul orașului.",
        real_sentence="Incinta exterioară în partea de est, astăzi goală, deținea altădată, donjonul construit pentru Filip al II-lea  în 1219, cu ocazia unei confiscări a senioriei, ca și Catedrala Colegială Saint-Ythier, mutată de Maximilien De Béthune  în interiorul orașului.",
        plot="decoder_layer2_block2")

# You can pass different layers and attention blocks of the decoder to the `plot` parameter.
correct("În prezent, satul are 3.897 locuitori, prepoderent ucraineni.",
        real_sentence="În prezent, satul are 3.897 locuitori, preponderent ucraineni.",
        plot="decoder_layer2_block2")

scores = 0.0
number = 0
for (inp, tar) in test_examples:
    score = correct(str(inp.numpy()), real_sentence=str(tar.numpy()),
                    verbose=False)
    print(score)
    if score is None:
        score = 0
    scores += score
    number += 1
print(f"BLEU score: {scores / number}")

"""## Summary"""

from google.colab import files
!zip -r /content/model.zip /content/checkpoints/train /content/logs
files.download("/content/model.zip")

"""All good!"""
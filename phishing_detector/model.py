"""BiLSTM model definition."""

import keras

from phishing_detector.config import EMBEDDING_DIM, MAX_SEQUENCE_LENGTH


def build_model(
    vocab_size: int,
    max_length: int = MAX_SEQUENCE_LENGTH,
    embedding_dim: int = EMBEDDING_DIM,
    recurrent_activation="sigmoid",
) -> keras.Model:
    """Character embedding -> 3 stacked bidirectional LSTMs -> sigmoid output."""

    def bilstm(units: int, return_sequences: bool) -> keras.layers.Layer:
        return keras.layers.Bidirectional(
            keras.layers.LSTM(
                units,
                dropout=0.3,
                recurrent_dropout=0.3,
                recurrent_activation=recurrent_activation,
                return_sequences=return_sequences,
            )
        )

    return keras.Sequential(
        [
            keras.Input(shape=(max_length,), dtype="int32"),
            keras.layers.Embedding(vocab_size, embedding_dim),
            bilstm(256, return_sequences=True),
            bilstm(256, return_sequences=True),
            bilstm(128, return_sequences=False),
            keras.layers.Dense(1, activation="sigmoid"),
        ],
        name="bilstm_url_classifier",
    )

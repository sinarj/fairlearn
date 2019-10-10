# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import copy
import numpy as np
import pandas as pd
import pytest
from fairlearn.post_processing._constants import DEMOGRAPHIC_PARITY, EQUALIZED_ODDS
from fairlearn.post_processing.threshold_optimizer import \
    (ThresholdOptimizer,
     _vectorized_prediction,
     _threshold_optimization_demographic_parity,
     _threshold_optimization_equalized_odds,
     DIFFERENT_INPUT_LENGTH_ERROR_MESSAGE,
     EMPTY_INPUT_ERROR_MESSAGE,
     NON_BINARY_LABELS_ERROR_MESSAGE,
     INPUT_DATA_FORMAT_ERROR_MESSAGE,
     NOT_SUPPORTED_PARITY_CRITERIA_ERROR_MESSAGE,
     PREDICT_BEFORE_FIT_ERROR_MESSAGE,
     MULTIPLE_DATA_COLUMNS_ERROR_MESSAGE)
from fairlearn.post_processing.post_processing import \
    MODEL_OR_ESTIMATOR_REQUIRED_ERROR_MESSAGE, EITHER_MODEL_OR_ESTIMATOR_ERROR_MESSAGE, \
    MISSING_FIT_PREDICT_ERROR_MESSAGE, MISSING_PREDICT_ERROR_MESSAGE
from .test_utilities import (example_attributes1, example_attributes2, example_labels,
                             example_scores, example_attribute_names1, example_attribute_names2,
                             _get_predictions_by_attribute, _format_as_list_of_lists,
                             ExampleModel, ExampleEstimator, ExampleNotModel,
                             ExampleNotEstimator1, ExampleNotEstimator2)


ALLOWED_INPUT_DATA_TYPES = [lambda x: x, np.array, pd.DataFrame, pd.Series]


@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("predict_method_name", ['predict', 'predict_proba'])
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_predict_before_fit_error(X_transform, A_transform, predict_method_name, metric):
    X = X_transform(_format_as_list_of_lists(example_attributes1))
    A = A_transform(example_attributes1)
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)

    with pytest.raises(ValueError, match=PREDICT_BEFORE_FIT_ERROR_MESSAGE):
        getattr(adjusted_model, predict_method_name)(X, A)


@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_both_model_and_estimator_error(metric):
    with pytest.raises(ValueError, match=EITHER_MODEL_OR_ESTIMATOR_ERROR_MESSAGE):
        ThresholdOptimizer(unconstrained_model=ExampleModel(),
                           unconstrained_estimator=ExampleEstimator(),
                           parity_criteria=metric)


@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_no_model_or_estimator_error(metric):
    with pytest.raises(ValueError, match=MODEL_OR_ESTIMATOR_REQUIRED_ERROR_MESSAGE):
        ThresholdOptimizer(parity_criteria=metric)


def test_metric_not_supported():
    with pytest.raises(ValueError, match=NOT_SUPPORTED_PARITY_CRITERIA_ERROR_MESSAGE):
        ThresholdOptimizer(unconstrained_model=ExampleModel(),
                           parity_criteria="UnsupportedMetric")


@pytest.mark.parametrize("not_estimator", [ExampleNotEstimator1(), ExampleNotEstimator2()])
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_not_estimator(not_estimator, metric):
    with pytest.raises(ValueError, match=MISSING_FIT_PREDICT_ERROR_MESSAGE):
        ThresholdOptimizer(unconstrained_estimator=not_estimator,
                           parity_criteria=metric)


@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_not_model(metric):
    with pytest.raises(ValueError, match=MISSING_PREDICT_ERROR_MESSAGE):
        ThresholdOptimizer(unconstrained_model=ExampleNotModel(),
                           parity_criteria=metric)


@pytest.mark.parametrize("X", [None, _format_as_list_of_lists(example_attributes1)])
@pytest.mark.parametrize("y", [None, example_labels])
@pytest.mark.parametrize("A", [None, example_attributes1])
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_inconsistent_input_data_types(X, y, A, metric):
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)

    error_message = INPUT_DATA_FORMAT_ERROR_MESSAGE.format(type(X).__name__,
                                                           type(y).__name__,
                                                           type(A).__name__)

    if X is None or y is None and A is None:
        with pytest.raises(TypeError) as exception:
            adjusted_model.fit(X, y, A)
        assert str(exception.value) == error_message


@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_threshold_optimization_non_binary_labels(X_transform, y_transform, A_transform,
                                                  metric):
    non_binary_labels = copy.deepcopy(example_labels)
    non_binary_labels[0] = 2

    X = X_transform(_format_as_list_of_lists(example_attributes1))
    y = y_transform(non_binary_labels)
    A = A_transform(example_attributes1)

    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)

    with pytest.raises(ValueError, match=NON_BINARY_LABELS_ERROR_MESSAGE):
        adjusted_model.fit(X, y, A)


@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_threshold_optimization_different_input_lengths(X_transform, y_transform,
                                                        A_transform, metric):
    n = len(example_attributes1)
    for permutation in [(0, 1), (1, 0)]:
        with pytest.raises(ValueError, match=DIFFERENT_INPUT_LENGTH_ERROR_MESSAGE
                           .format("X, aux_data, and y")):
            X = X_transform(_format_as_list_of_lists(
                example_attributes1)[:n - permutation[0]])
            y = y_transform(example_labels[:n - permutation[1]])
            A = A_transform(example_attributes1)

            adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                                parity_criteria=metric)
            adjusted_model.fit(X, y, A)

    # try providing empty lists in all combinations
    for permutation in [(0, n), (n, 0)]:
        X = X_transform(_format_as_list_of_lists(
            example_attributes1)[:n - permutation[0]])
        y = y_transform(example_labels[:n - permutation[1]])
        A = A_transform(example_attributes1)

        adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                            parity_criteria=metric)
        with pytest.raises(ValueError, match=EMPTY_INPUT_ERROR_MESSAGE):
            adjusted_model.fit(X, y, A)


@pytest.mark.parametrize("score_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
def test_threshold_optimization_demographic_parity(score_transform, y_transform,
                                                   A_transform):
    y = y_transform(example_labels)
    A = A_transform(example_attributes1)
    scores = score_transform(example_scores)
    adjusted_model = create_adjusted_model(_threshold_optimization_demographic_parity,
                                           A, y, scores)

    # For Demographic Parity we can ignore p_ignore since it's always 0.

    # attribute value A
    value_for_less_than_2_5 = 0.8008
    assert np.isclose(value_for_less_than_2_5,
                      adjusted_model([example_attribute_names1[0]], [0]))
    assert np.isclose(value_for_less_than_2_5,
                      adjusted_model([example_attribute_names1[0]], [2.499]))
    assert 0 == adjusted_model([example_attribute_names1[0]], [2.5])
    assert 0 == adjusted_model([example_attribute_names1[0]], [100])

    # attribute value B
    value_for_less_than_0_5 = 0.00133333333333
    assert np.isclose(value_for_less_than_0_5,
                      adjusted_model([example_attribute_names1[1]], [0]))
    assert np.isclose(value_for_less_than_0_5,
                      adjusted_model([example_attribute_names1[1]], [0.5]))
    assert 1 == adjusted_model([example_attribute_names1[1]], [0.51])
    assert 1 == adjusted_model([example_attribute_names1[1]], [1])
    assert 1 == adjusted_model([example_attribute_names1[1]], [100])

    # attribute value C
    value_between_0_5_and_1_5 = 0.608
    assert 0 == adjusted_model([example_attribute_names1[2]], [0])
    assert 0 == adjusted_model([example_attribute_names1[2]], [0.5])
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [0.51]))
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [1]))
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [1.5]))
    assert 1 == adjusted_model([example_attribute_names1[2]], [1.51])
    assert 1 == adjusted_model([example_attribute_names1[2]], [100])

    # Assert Demographic Parity actually holds
    predictions_by_attribute = _get_predictions_by_attribute(adjusted_model, example_attributes1,
                                                             example_scores, example_labels)

    average_probabilities_by_attribute = \
        [np.sum([lp.prediction for lp in predictions_by_attribute[attribute_value]])
         / len(predictions_by_attribute[attribute_value])
         for attribute_value in sorted(predictions_by_attribute)]
    assert np.isclose(average_probabilities_by_attribute, [0.572] * 3).all()


@pytest.mark.parametrize("score_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
def test_threshold_optimization_equalized_odds(score_transform, y_transform,
                                               A_transform):
    y = y_transform(example_labels)
    A = A_transform(example_attributes1)
    scores = score_transform(example_scores)
    adjusted_model = create_adjusted_model(_threshold_optimization_equalized_odds,
                                           A, y, scores)

    # For Equalized Odds we need to factor in that the output is calculated by
    # p_ignore * prediction_constant + (1 - p_ignore) * (p0 * pred0(x) + p1 * pred1(x))
    # with p_ignore != 0 and prediction_constant != 0 for at least some attributes values.
    prediction_constant = 0.334

    # attribute value A
    # p_ignore is almost 0 which means there's almost no adjustment
    p_ignore = 0.001996007984031716
    base_value = prediction_constant * p_ignore
    value_for_less_than_2_5 = base_value + (1 - p_ignore) * 0.668

    assert np.isclose(value_for_less_than_2_5,
                      adjusted_model([example_attribute_names1[0]], [0]))
    assert np.isclose(value_for_less_than_2_5,
                      adjusted_model([example_attribute_names1[0]], [2.499]))
    assert base_value == adjusted_model([example_attribute_names1[0]], [2.5])
    assert base_value == adjusted_model([example_attribute_names1[0]], [100])

    # attribute value B
    # p_ignore is the largest among the three classes indicating a large adjustment
    p_ignore = 0.1991991991991991
    base_value = prediction_constant * p_ignore
    value_for_less_than_0_5 = base_value + (1 - p_ignore) * 0.001
    assert np.isclose(value_for_less_than_0_5,
                      adjusted_model([example_attribute_names1[1]], [0]))
    assert np.isclose(value_for_less_than_0_5,
                      adjusted_model([example_attribute_names1[1]], [0.5]))
    assert base_value + 1 - \
        p_ignore == adjusted_model([example_attribute_names1[1]], [0.51])
    assert base_value + 1 - \
        p_ignore == adjusted_model([example_attribute_names1[1]], [1])
    assert base_value + 1 - \
        p_ignore == adjusted_model([example_attribute_names1[1]], [100])

    # attribute value C
    # p_ignore is 0 which means there's no adjustment
    p_ignore = 0
    base_value = prediction_constant * p_ignore
    value_between_0_5_and_1_5 = base_value + (1 - p_ignore) * 0.501
    assert base_value == adjusted_model([example_attribute_names1[2]], [0])
    assert base_value == adjusted_model([example_attribute_names1[2]], [0.5])
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [0.51]))
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [1]))
    assert np.isclose(value_between_0_5_and_1_5,
                      adjusted_model([example_attribute_names1[2]], [1.5]))
    assert base_value + 1 - \
        p_ignore == adjusted_model([example_attribute_names1[2]], [1.51])
    assert base_value + 1 - \
        p_ignore == adjusted_model([example_attribute_names1[2]], [100])

    # Assert Equalized Odds actually holds
    predictions_by_attribute = _get_predictions_by_attribute(adjusted_model, example_attributes1,
                                                             example_scores, example_labels)

    predictions_based_on_label = {}
    for label in [0, 1]:
        predictions_based_on_label[label] = \
            [np.sum([lp.prediction for lp in predictions_by_attribute[attribute_value]
                     if lp.label == label])
             / len([lp for lp in predictions_by_attribute[attribute_value] if lp.label == label])
             for attribute_value in sorted(predictions_by_attribute)]

    # assert counts of positive predictions for negative labels
    assert np.isclose(predictions_based_on_label[0], [0.334] * 3).all()
    # assert counts of positive predictions for positive labels
    assert np.isclose(predictions_based_on_label[1], [0.66733333] * 3).all()


@pytest.mark.parametrize("attributes,attribute_names,expected_p0,expected_p1",
                         [(example_attributes1, example_attribute_names1, 0.428, 0.572),
                          (example_attributes2, example_attribute_names2, 0.6, 0.4)])
@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
def test_threshold_optimization_demographic_parity_e2e(attributes, attribute_names,
                                                       expected_p0, expected_p1,
                                                       X_transform, y_transform,
                                                       A_transform):
    X = X_transform(_format_as_list_of_lists(attributes))
    y = y_transform(example_labels)
    A = A_transform(attributes)
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=DEMOGRAPHIC_PARITY)
    adjusted_model.fit(X, y, A)

    predictions = adjusted_model.predict_proba(X, A)

    # assert demographic parity
    for a in attribute_names:
        average_probs = np.average(
            predictions[np.array(attributes) == a], axis=0)
        assert np.isclose(average_probs[0], expected_p0)
        assert np.isclose(average_probs[1], expected_p1)


@pytest.mark.parametrize("attributes,attribute_names,"
                         "expected_positive_p0,expected_positive_p1,"
                         "expected_negative_p0,expected_negative_p1",
                         [(example_attributes1, example_attribute_names1,
                           0.33266666, 0.66733333, 0.666, 0.334),
                          (example_attributes2, example_attribute_names2,
                           0.112, 0.888, 0.334, 0.666)])
@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
def test_threshold_optimization_equalized_odds_e2e(
        attributes, attribute_names, expected_positive_p0, expected_positive_p1,
        expected_negative_p0, expected_negative_p1, X_transform, y_transform, A_transform):
    X = X_transform(_format_as_list_of_lists(attributes))
    y = y_transform(example_labels)
    A = A_transform(attributes)
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=EQUALIZED_ODDS)
    adjusted_model.fit(X, y, A)

    predictions = adjusted_model.predict_proba(X, A)

    # assert equalized odds
    for a in attribute_names:
        positive_indices = (np.array(attributes) == a) * \
            (np.array(example_labels) == 1)
        negative_indices = (np.array(attributes) == a) * \
            (np.array(example_labels) == 0)
        average_probs_positive_indices = np.average(
            predictions[positive_indices], axis=0)
        average_probs_negative_indices = np.average(
            predictions[negative_indices], axis=0)
        assert np.isclose(
            average_probs_positive_indices[0], expected_positive_p0)
        assert np.isclose(
            average_probs_positive_indices[1], expected_positive_p1)
        assert np.isclose(
            average_probs_negative_indices[0], expected_negative_p0)
        assert np.isclose(
            average_probs_negative_indices[1], expected_negative_p1)


@pytest.mark.parametrize("attributes,attribute_names",
                         [(example_attributes1, example_attribute_names1),
                          (example_attributes2, example_attribute_names2)])
@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_predict_output_0_or_1(attributes, attribute_names, X_transform, y_transform, A_transform,
                               metric):
    X = X_transform(_format_as_list_of_lists(attributes))
    y = y_transform(example_labels)
    A = A_transform(attributes)
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)
    adjusted_model.fit(X, y, A)

    predictions = adjusted_model.predict(X, A)
    for prediction in predictions:
        assert prediction in [0, 1]


@pytest.mark.parametrize("attributes,attribute_names",
                         [(example_attributes1, example_attribute_names1),
                          (example_attributes2, example_attribute_names2)])
@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_predict_multiple_attributes_columns_error(attributes, attribute_names, X_transform,
                                                   y_transform, metric):
    X = X_transform(_format_as_list_of_lists(attributes))
    y = y_transform(example_labels)
    A = pd.DataFrame({"A1": attributes, "A2": attributes})
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)
    adjusted_model.fit(X, y, attributes)

    with pytest.raises(ValueError,
                       match=MULTIPLE_DATA_COLUMNS_ERROR_MESSAGE.format("group_data")):
        adjusted_model.predict(X, A)


@pytest.mark.parametrize("attributes,attribute_names",
                         [(example_attributes1, example_attribute_names1),
                          (example_attributes2, example_attribute_names2)])
@pytest.mark.parametrize("X_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("y_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("A_transform", ALLOWED_INPUT_DATA_TYPES)
@pytest.mark.parametrize("metric", [DEMOGRAPHIC_PARITY, EQUALIZED_ODDS])
def test_predict_different_argument_lengths(attributes, attribute_names, X_transform, y_transform,
                                            A_transform, metric):
    X = X_transform(_format_as_list_of_lists(attributes))
    y = y_transform(example_labels)
    A = A_transform(attributes)
    adjusted_model = ThresholdOptimizer(unconstrained_model=ExampleModel(),
                                        parity_criteria=metric)
    adjusted_model.fit(X, y, A)

    with pytest.raises(ValueError, match=DIFFERENT_INPUT_LENGTH_ERROR_MESSAGE
                       .format("X and aux_data")):
        adjusted_model.predict(X, A_transform(attributes[:-1]))

    with pytest.raises(ValueError, match=DIFFERENT_INPUT_LENGTH_ERROR_MESSAGE
                       .format("X and aux_data")):
        adjusted_model.predict(X_transform(
            _format_as_list_of_lists(attributes))[:-1], A)


def create_adjusted_model(threshold_optimization_method, example_attributes,
                          example_labels, example_scores):
    post_processed_model_by_attribute = threshold_optimization_method(
        example_attributes, example_labels, example_scores)

    return lambda A, scores: _vectorized_prediction(post_processed_model_by_attribute, A, scores)
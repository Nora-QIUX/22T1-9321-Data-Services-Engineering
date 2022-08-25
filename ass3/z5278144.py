import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn import metrics
from scipy.stats import pearsonr
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso, Ridge
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_selection import f_classif
from sklearn.feature_selection import SelectKBest, SelectFromModel
from sklearn.ensemble import ExtraTreesClassifier

if __name__ == "__main__":

    df_train = pd.read_csv(sys.argv[1])
    df_test = pd.read_csv(sys.argv[2])
    # df_train = pd.read_csv('training.csv')
    # df_test = pd.read_csv('test.csv')
    train = df_train.copy()
    test = df_test.copy()

    ######################## Part-I: Regression ########################

    # filter_columns
    percent = train.isnull().sum() / train.notnull().count()
    columns_filtered = percent[percent < 0.5].index.values
    train = train[columns_filtered]
    test = test[columns_filtered]

    # remove nan
    # print(train.info())
    object_features = train.select_dtypes('object').columns
    IMP = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
    train = IMP.fit_transform(train)
    train = pd.DataFrame(train, columns=columns_filtered)
    test = IMP.fit_transform(test)
    test = pd.DataFrame(test, columns=columns_filtered)

    # label encode
    # print(train.info())
    LE = LabelEncoder()
    for i in object_features:
        train[i] = LE.fit_transform(train[i])
        test[i] = LE.fit_transform(test[i])

    # outlier row filter
    ISF = IsolationForest(contamination=0.1)
    output = ISF.fit_predict(train.values)
    mask_output = output != -1
    train = train[mask_output]

    # split x, y
    y_train = train["AMT_INCOME_TOTAL"]
    x_train = train.drop("AMT_INCOME_TOTAL", axis=1)
    y_test = test["AMT_INCOME_TOTAL"]
    x_test = test.drop("AMT_INCOME_TOTAL", axis=1)

    # select feature for regression
    SFM = SelectFromModel(Lasso(alpha=100), max_features=10)
    SFM.fit(x_train, y_train)
    features_for_reg = x_train.columns.values
    x_test = x_test[features_for_reg]  # df

    # scaler for regression
    SS = StandardScaler()
    x_train = SS.fit_transform(x_train.values)
    # y_train = np.log(y_train)
    # y_train[np.isinf(y_train)] = 0
    x_test = SS.transform(x_test.values)
    # y_test = np.log(y_test)
    # y_test[np.isinf(y_test)] = 0

    model = Ridge()

    model.fit(x_train, y_train)
    predicted_INCOME = model.predict(x_test)

    mse = metrics.mean_squared_error(y_test, predicted_INCOME)
    correlation, _ = pearsonr(predicted_INCOME, y_test)

    print('################# mse,correlation #################')
    print(mse, correlation)

    zid = 'z5278144'
    # pd.DataFrame({'SK_ID_CURR': test['SK_ID_CURR'].values, 'predicted_income': np.exp(2*predicted_INCOME).astype(np.int)},
    #              columns=['SK_ID_CURR', 'predicted_income']).to_csv(zid + '.PART1.output.csv', index=False)
    pd.DataFrame({'SK_ID_CURR': test['SK_ID_CURR'].values, 'predicted_income': predicted_INCOME},
                 columns=['SK_ID_CURR', 'predicted_income']).to_csv(zid + '.PART1.output.csv', index=False)
    pd.DataFrame([[zid, round(mse, 2), round(correlation, 2)]], columns=['zid', 'MSE', 'correlation']).to_csv(
                 zid + '.PART1.summary.csv', index=False)

    ######################## Part-II: Classification ########################

    train = df_train.copy()
    test = df_test.copy()

    # filter_columns
    percent = train.isnull().sum() / train.notnull().count()
    columns_filtered = percent[percent < 0.5].index.values
    train = train[columns_filtered]
    percent = test.isnull().sum() / test.notnull().count()
    columns_filtered = percent[percent < 0.5].index.values
    test = test[columns_filtered]

    # remove nan
    IMP = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
    train = IMP.fit_transform(train)
    train = pd.DataFrame(train, columns=columns_filtered)
    test = IMP.fit_transform(test)
    test = pd.DataFrame(test, columns=columns_filtered)

    # single_removal
    single_column = train.columns[train.apply(lambda x: len(x.unique())) == 1].values
    train = train.drop(columns=single_column)
    single_column = test.columns[test.apply(lambda x: len(x.unique())) == 1].values
    test = test.drop(columns=single_column)

    # label encoder
    LE = LabelEncoder()
    for i in train.select_dtypes(include="object").columns:
        train[i] = LE.fit_transform(train[i])
    for i in test.select_dtypes(include="object").columns:
        test[i] = LE.fit_transform(test[i])

    # split
    y_train = train['TARGET']
    x_train = train.drop(columns=['TARGET'])

    y_test = test['TARGET']
    x_test = test.drop(columns=['TARGET'])

    # y_train = y_train.values.reshape(-1, 1)
    # print(type(x_train), type(y_train), x_train.shape, y_train.shape)

    # select features
    SKB = SelectKBest(f_classif, k=13)  ##10
    # SKB.fit(x_train, y_train.reshape(-1, 1))
    SKB.fit(x_train, y_train)
    features_selected = x_train.columns[SKB.get_support()]
    x_train, x_test = x_train[features_selected], x_test[features_selected]
    x_train['SK_ID_CURR'], x_test['SK_ID_CURR'] = train['SK_ID_CURR'], test['SK_ID_CURR']

    model = ExtraTreesClassifier()

    model.fit(x_train, y_train)
    predicted_target = model.predict(x_test)

    report = classification_report(y_test, predicted_target, output_dict=True)
    print('################# acc,pre,recall #################')
    print(report["accuracy"], report["macro avg"]["precision"], report["macro avg"]["recall"])

    zid = 'z5278144'
    pd.DataFrame({'SK_ID_CURR': test['SK_ID_CURR'].values, 'predicted_target': predicted_target}, columns=[
        'SK_ID_CURR', 'predicted_target']).to_csv(zid + '.PART2.output.csv', index=False)
    pd.DataFrame([[zid, round(report["macro avg"]["precision"], 2), round(report["macro avg"]["recall"], 2),
                   round(report["accuracy"], 2)]], columns=['zid', 'average_precision', 'average_recall', 'accuracy']).\
                    to_csv(zid + '.PART2.summary.csv', index=False)

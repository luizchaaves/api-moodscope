import os
import pandas as pd
from leia import SentimentIntensityAnalyzer as SentimentPortuguese
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as SentimentEnglish
from flask import Flask, jsonify
from marshmallow import Schema, fields
import re
from flask_cors import CORS
from stop_words import get_stop_words
from nltk.tokenize import word_tokenize

analyzerPortuguese = SentimentPortuguese()
analyzerEnglish = SentimentEnglish()

positiveComments = []
negativeComments = []
neutralComments = []


class SentimentDataSchema(Schema):
    quantity = fields.Integer()
    percentual = fields.String()


class AnalyseResultsSchemaEnderecoSchema(Schema):
    videoTittle = fields.String()
    commentsTotal = fields.Integer()
    commentsPositive = fields.Nested(SentimentDataSchema)
    commentsNegative = fields.Nested(SentimentDataSchema)
    commentsNeutral = fields.Nested(SentimentDataSchema)


class FileDataSchema(Schema):
    fileName = fields.Integer()
    videoTittle = fields.String()


sentimentData_schema = SentimentDataSchema()
analyseResults_schema = AnalyseResultsSchemaEnderecoSchema()
fileDataSchema_schema = FileDataSchema()

# Função para calcular o sentimento dos comentários


def setScore(comment, language):
    if (language == 'pt'):
        try:
            return analyzerPortuguese.polarity_scores(comment)
        except:
            return 'undefined'
    else:
        try:
            return analyzerEnglish.polarity_scores(comment)
        except:
            return 'undefined'

# Função para preencher as listas com os comentários e os sentimentos geradas pelo vader


def writeCommentInfo(comment, score):
    scoreNegative = score['neg']
    scoreNeutral = score['neu']
    scorePositive = score['pos']
    scoreCompound = score['compound']

    if (scoreCompound >= 0.05):
        positiveComments.append({'comment': comment, 'score negative': scoreNegative,
                                'score neutral': scoreNeutral, 'score positive': scorePositive, 'score compound': scoreCompound})
    elif (scoreCompound <= -0.05):
        negativeComments.append({'comment': comment, 'score negative': scoreNegative,
                                'score neutral': scoreNeutral, 'score positive': scorePositive, 'score compound': scoreCompound})
    else:
        neutralComments.append({'comment': comment, 'score negative': scoreNegative,
                               'score neutral': scoreNeutral, 'score positive': scorePositive, 'score compound': scoreCompound})

# Função para calcular as estatística dos comentários


def commentStatistics(commentFileNameToSearch):
    totalComments = len(negativeComments) + \
        len(neutralComments) + len(positiveComments)
    percentagePositive = round(
        (len(positiveComments) / totalComments) * 100, 2)
    percentageNegative = round(
        (len(negativeComments) / totalComments) * 100, 2)
    percentageNeutral = round((len(neutralComments) / totalComments) * 100, 2)

    commentsPositive = {
        'quantity': len(positiveComments),
        'percentual': str(percentagePositive) + "%"
    }

    commentsNegative = {
        'quantity': len(negativeComments),
        'percentual': str(percentageNegative) + "%"
    }

    commentsNeutral = {
        'quantity': len(neutralComments),
        'percentual': str(percentageNeutral) + "%"
    }

    analyseResults = {
        'videoTittle': commentFileNameToSearch,
        'commentsTotal': totalComments,
        'commentsPositive': commentsPositive,
        'commentsNegative': commentsNegative,
        'commentsNeutral': commentsNeutral
    }

    exportCsv(analyseResults)
    result = analyseResults_schema.dump(analyseResults)

    return result

# Função para exportar as listas de comentários para .CSV


def exportCsv(result):
    csvPositiveComments = pd.DataFrame(positiveComments)
    csvPositiveComments.to_csv(
        './result/PositiveComments.csv', sep=';', index=False)

    csvNegativeComments = pd.DataFrame(negativeComments)
    csvNegativeComments.to_csv(
        './result/NegativeComments.csv', sep=';', index=False)

    csvNeutralComments = pd.DataFrame(neutralComments)
    csvNeutralComments.to_csv(
        './result/NeutralComments.csv', sep=';', index=False)

    csvAnalyseResult = pd.DataFrame(result)
    csvAnalyseResult.to_csv(
        './result/AnalyseResult.csv', sep=';', index=False)

# Função para buscar o nome do arquivo selecionado dentro da lista de arquivos da pasta comments


def fetchFile(listCommentFileNames, name):
    for filename in listCommentFileNames:
        if name == filename:
            return True
    return False


def processAnalyse(videoName):
    folderComments = './comments'
    listCommentFileNames = []

    commentFileNameToSearch = videoName + '.csv'

    # Acessa a pasta comments e armazena o nome dos arquivos na lista
    for file in os.listdir(folderComments):
        if os.path.isfile(os.path.join(folderComments, file)):
            listCommentFileNames.append(file)

    if fetchFile(listCommentFileNames, commentFileNameToSearch):
        path = './comments/' + str(commentFileNameToSearch)
        fileComments = pd.read_csv(path)
        commentsList = fileComments.iloc[:, 1].tolist()
        languagesList = fileComments.iloc[:, 2].tolist()

        for comment, language in zip(commentsList, languagesList):
            score = setScore(comment, language)
            if (score != 'undefined'):
                writeCommentInfo(comment, score)

        # Process video tittle
        videoTittle = processVideoTittle(videoName)

        result = commentStatistics(videoTittle)
        return result
    else:
        return ('Arquivo não encontrado!')


def getComments(videoName):
    folderComments = './comments'
    listCommentFileNames = []

    commentFileNameToSearch = videoName + '.csv'

    # Acessa a pasta comments e armazena o nome dos arquivos na lista
    for file in os.listdir(folderComments):
        if os.path.isfile(os.path.join(folderComments, file)):
            listCommentFileNames.append(file)

    if fetchFile(listCommentFileNames, commentFileNameToSearch):
        stopwords_en = get_stop_words('english')
        stopwords_pt = get_stop_words('portuguese')
        
        path = './comments/' + str(commentFileNameToSearch)
        fileComments = pd.read_csv(path)
        commentsList = fileComments.iloc[:, 1].tolist()

        string = '|;| '.join(str(elemento) for elemento in commentsList)
        tokens = word_tokenize(string)
        filtered_words = [word for word in tokens if word.lower() not in stopwords_en and word.lower() not in stopwords_pt]
        filtered_text = ' '.join(filtered_words)
        lista = filtered_text.split('|;|')

        return lista
    else:
        return ('Arquivo não encontrado!')


def getFiles():
    folderComments = './comments'
    listCommentFileNames = []

    # Acessa a pasta comments e armazena o nome dos arquivos na lista
    for file in os.listdir(folderComments):
        if os.path.isfile(os.path.join(folderComments, file)):
            fileInfo = {
                'fileName': file,
                'videoTittle': processVideoTittle(file)
            }
            listCommentFileNames.append(fileInfo)

    return listCommentFileNames


def processVideoTittle(file):
    regexRemoveCSV = r'\.csv'
    videoTittle = re.sub(regexRemoveCSV, '', file)
    regexRemoveYoutube = r'YouTube'
    videoTittle = re.sub(regexRemoveYoutube, '', videoTittle)
    regexSplitWords = r'([a-z])([A-Z0-9])'
    videoTittle = re.sub(regexSplitWords, r'\1 \2', videoTittle)

    return videoTittle


# API code
app = Flask(__name__)
CORS(app)


@app.route('/analyse/<string:videoName>', methods=['GET'])
def get_analyse_result(videoName):
    positiveComments.clear()
    negativeComments.clear()
    neutralComments.clear()
    result = processAnalyse(videoName)
    return jsonify(result)


@app.route('/comments/<string:videoName>', methods=['GET'])
def get_comments(videoName):
    result = getComments(videoName)
    return jsonify(result)


@app.route('/files', methods=['GET'])
def get_files():
    result = getFiles()
    return jsonify(result)


app.run(port=5000, host='localhost', debug=True)

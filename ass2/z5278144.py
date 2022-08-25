import json

import requests
from datetime import datetime,timedelta
from flask import Flask, request, send_file, make_response, jsonify
from flask_restx import Resource, Api, reqparse, fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate #pip install flask_migrate
# from flask_script import Manager#####
import sqlite3
import numpy as np
import matplotlib.pyplot as plt

app = Flask(__name__)
api = Api(app, title="REST API for Actor/Actress",
          description="a Flask-Restx data service that allows a client to read and store some actor/actress information, and allow the consumers to access the data.",
          default="Operation Collections")
# manager = Manager(app)####
import os

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///z5278144.db' #设置
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///z5278144.db" #先写这个再写db=SQLAlchemy(app)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True #warning解决了
db = SQLAlchemy(app) #数据库
app.config["JSON_SORT_KEYS"]= False
migrate = Migrate(app,db)#过程

class ActorsDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_update = db.Column(db.DateTime,default = datetime.now())
    name = db.Column(db.String(100), unique=True, nullable=False)
    gender = db.Column(db.String(5), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    birthday = db.Column(db.DateTime, nullable=True)
    deathday = db.Column(db.DateTime, nullable=True)
    show = db.Column(db.Text, nullable=True)
    # SQLALCHEMY_TRACK_MODIFICATIONS = True
    # SQLALCHEMY_COMMIT_TEARDOWN = True
    def __repr__(self):
        # return f"id:{self.id},name:{self.name}"
        pass

db.create_all()#写在class上面出错

actor_post_rep = reqparse.RequestParser()
actor_post_rep.add_argument("name",type=str)

actors_list_rep = reqparse.RequestParser()
actors_list_rep.add_argument("order",type=str, default=["+id"], action="split")
actors_list_rep.add_argument("page",type=int, default=1)
actors_list_rep.add_argument("size",type=int, default=10)
actors_list_rep.add_argument("filter",type=str, default=["id,name"], action="split")

actors_statistics_rep = reqparse.RequestParser()
actors_statistics_rep.add_argument("format",type=str)
actors_statistics_rep.add_argument("by",type=str, action="split")

# resource_field = {
#     "id": fields.Integer,
#     "name": fields.String,
#     "age": fields.Integer
# }

@api.route("/actors") #装置器声明方法一  "/"代表路径
class Q1_Actor_add_Q5_List_get(Resource):
    @api.expect(actor_post_rep)
    # @marshal_with(resource_field)
    def post(self):#post/Add a new Actor
        args = actor_post_rep.parse_args()
        name = args["name"]
        for char in ["-","?","_",",","."]:
            name=name.replace(char," ")
        people_url = "https://api.tvmaze.com/search/people?q="+name
        actor_request = requests.get(people_url)
        if actor_request.status_code >= 200 and actor_request.status_code < 300:
            actor_dict = actor_request.json()[0] #也可等于json.loads(ac_reqst.text)[0]
            print(actor_dict)
            actor_info_dict = actor_dict["person"] #actor_info依然是字典

        actor_id = actor_info_dict["id"]
        name = actor_info_dict["name"]
        country = None
        if actor_info_dict["country"]:
            country = actor_info_dict["country"]["name"]
        birthday = actor_info_dict["birthday"]
        deathday = actor_info_dict["deathday"]
        gender = actor_info_dict["gender"]
        show_list_url = "https://api.tvmaze.com/people/" + str(actor_id) + "/castcredits"
        show_list_request = requests.get(show_list_url)
        # if show_list_request.status_code == 200:
        #     show_list_text = show_list_request #也可等于json.loads(show_list_reqt.text)
        show_list=[]

        for show_dict in show_list_request.json():
            show_url = show_dict["_links"]["show"]["href"]
            show_request = requests.get(show_url)
            # if show_request.status_code == 200:
            #     show_text = json.loads(show_request.text)
            show_list.append(show_request.json()["name"])

        show_str = " , ".join(show_list)
        if birthday:
            birthday = datetime.strptime(birthday, "%Y-%m-%d")
        if deathday:
            deathday = datetime.strptime(deathday, "%Y-%m-%d") #提取出datetime 把它格式化为字符串 固定显示
        actor = ActorsDB(name=name, gender=gender, country=country, birthday=birthday, deathday=deathday, show=show_str)
        post_before = ActorsDB.query.filter_by(name=name).first() #判断之前添加了没有
        if not post_before:
            db.session.add(actor)
            db.session.commit()
        actor = ActorsDB.query.filter_by(name=name).first()
        return {"id": actor.id,
                "last_update": actor.last_update.strftime("%Y-%m-%d-%H:%M:%S"), #时间类型改成str且固定形式,
                "_links": {
                    "self": {
                        "href": "http://127.0.0.1:5000/actors/"+str(actor.id)
                    }
                }
                }, 200

    @api.expect(actors_list_rep)
    def get(self): # get/Retrieve the list of available Actors
        args = actors_list_rep.parse_args()
        order_by = args["order"]
        page = args["page"]
        size = args["size"]
        display_by = args["filter"]
        display_by_list = []
        for param in display_by:
            display_by_list.append(eval("ActorsDB."+param))
        print(order_by)
        order_by_list = []
        for attribute in order_by:
            if attribute[0] == "+":
                order_by_list.append(eval("ActorsDB."+attribute[1:] + ".asc()"))
            if attribute[0] == "-":
                order_by_list.append(eval("ActorsDB."+attribute[1:] + ".desc()"))
        print(order_by_list)
        actors_list = db.session.query(*display_by_list).order_by(*order_by_list).paginate(int(page), int(size), False)   #分页 !!list加了指针之后可以按顺序对list中的每个参数都进行使用
        return_list=[]
        for actor in actors_list.items: #items
            return_list.append({str(display_by_list[i]):actor[i] for i in range(len(display_by_list))})
        next_href = None
        if actors_list.has_next:
            next_href="http://127.0.0.1:5000/actors/order="+','.join(order_by)+"&page="+str(page+1)+"&size="+str(size)+"&filter="+','.join(display_by)
        return_message= {
                    "page": page,
                    "page-size": size,
                    "actors": return_list,
                    "_links": {
                        "self": {
                          "href": "http://127.0.0.1:5000/actors/order="+','.join(order_by)+"&page="+str(page)+"&size="+str(size)+"&filter="+','.join(display_by)
                                },
                        "next": {
                          "href": next_href
                                }
                              }
               }
        return make_response(jsonify(return_message),200)

@api.route("/actors/<int:actor_id>") #装置器声明方法一  "/"代表路径
class Q2_Q3_Q4_Actor_edit(Resource):
    def get(self,actor_id):# get/Retrieve an Actor
        actor = ActorsDB.query.get_or_404(actor_id)
        birthday = actor.birthday
        if actor.birthday:
            birthday = actor.birthday.strftime("%d-%m-%Y")
        deathday = actor.deathday
        if actor.deathday:
            deathday = actor.deathday.strftime("%d-%m-%Y")
        show = actor.show.split(" , ")
        previous = ActorsDB.query.order_by(ActorsDB.id.desc()).filter(ActorsDB.id < actor.id).first()
        next = ActorsDB.query.order_by(ActorsDB.id.asc()).filter(ActorsDB.id > actor.id).first()
        prev_href = None
        if previous:
            prev_href="http://127.0.0.1:5000/actors/" + str(previous.id)
        next_href = None
        if next:
            next_href="http://127.0.0.1:5000/actors/" + str(next.id)
        return {"id": actor.id,
                "last_update": actor.last_update.strftime("%Y-%m-%d-%H:%M:%S"),
                "name": actor.name,
                "country": actor.country,
                "birthday": birthday,
                "deathday": deathday,
                "show": show,
                "_links": {
                    "self": {
                        "href": "http://127.0.0.1:5000/actors/" + str(actor.id)
                    },
                    "previous": {
                        "href": prev_href,
                    },
                    "next": {
                        "href": next_href,
                    }
                }
                },200

    # @api.response(200,"Success")
    # @api.response(404,"ERROR")
    def delete(self,actor_id):#Deleting an Actor
        actor_delete = ActorsDB.query.get_or_404(actor_id)
        db.session.delete(actor_delete)
        db.session.commit()
        return {
                "message": "The actor with id "+str(actor_delete.id)+" was removed from the database!",
                "id": actor_delete.id
        }, 200
    def patch(self,actor_id):#patch/Update an Actor
        actor_update = ActorsDB.query.get_or_404(actor_id)
        update_data = request.get_json()
        update_data = json.loads(json.dumps(update_data))
        #print(type(update_data))#"<class 'method'>"
        Changed = False
        for attribute,value in update_data.items():
            if attribute in ["birthday","deathday"] and value:
                value = datetime.strptime(value,"%d-%m-%Y")
            if getattr(actor_update,attribute) != value:
                Changed = True
                setattr(actor_update,attribute,value)
        if Changed:
            actor_update.last_update = datetime.now()
        db.session.commit()
        actor = ActorsDB.query.get_or_404(actor_id)
        return {"id": actor.id,
                "last_update": actor.last_update.strftime("%Y-%m-%d-%H:%M:%S"),
                "_links": {
                    "self": {
                        "href": "http://127.0.0.1:5000/actors/" + str(actor.id)
                    }
                }
                }, 200

@api.route("/actors/statistics")
class Q6_Actors_statistics(Resource):
    @api.expect(actors_statistics_rep)
    def get(self):# get the statistics of the existing Actors
        args = actors_statistics_rep.parse_args()
        format_info = args["format"]
        group_by = args["by"]
        total = ActorsDB.query.count()
        total_update = ActorsDB.query.filter(ActorsDB.last_update > (datetime.today() - timedelta(days=1))).count()
        return_json = {"total": total,
                       "total-updated": total_update}

        plt.style.use('seaborn-pastel')

        fig,axes = plt.subplots(len(group_by),1,figsize=(8, 8))
        image=-1
        if "country" in group_by:
            group_by_country = db.session.query(ActorsDB.country, db.func.count(ActorsDB.id).label("sum")).group_by(ActorsDB.country).all()
            country_list = [value["country"] for value in group_by_country]
            sum_list = np.array([value["sum"] for value in group_by_country])
            deci_list = list(sum_list/sum_list.sum())
            return_json["by-country"] = {country_list[i]: deci_list[i] for i in range(len(deci_list))}
            country_list = [str(data["country"]) for data in group_by_country]

            image+= 1
            axes[image].pie(x=deci_list,labels=country_list,autopct='%.1f%%')

        if "birthday" in group_by:
            all_birthday = db.session.query(ActorsDB.birthday).all()
            age_list = []
            youth=0
            old=0
            for data in all_birthday:
                if data.birthday:
                    age = int(datetime.now().strftime("%Y")) - int(data.birthday.strftime("%Y"))
                    age_list.append(age)
                    if age<=30:
                        youth+=1
                    if age>=50:
                        old+=1
            age_list = np.array(age_list)

            return_json["by-birthday"] = {"age<=30":youth/total,
                                          "30<age<50":(total-youth-old)/total,
                                          "age>=50":old/total}
            image += 1
            axes[image].pie(x=[youth/total,(total-youth-old)/total,old/total],labels=["age<=30","30<age<50","age>_50"],autopct='%.1f%%')

        if "gender" in group_by:
            group_by_gender = db.session.query(ActorsDB.gender, db.func.count(ActorsDB.id).label("total")).group_by(
                ActorsDB.gender).all()
            gender_list = [data["gender"] for data in group_by_gender]
            sum_list = np.array([data["total"] for data in group_by_gender])
            deci_list = list(sum_list / sum_list.sum())
            return_json["by-gender"] = {gender_list[i]: deci_list[i] for i in range(len(deci_list))}
            gender_list = [str(data["gender"]) for data in group_by_gender]

            image += 1
            axes[image].pie(x=deci_list, labels=gender_list, autopct='%.1f%%')
        if "life_status" in group_by:
            dead=ActorsDB.query.filter(ActorsDB.deathday==None).count()
            live=total-dead
            x=[live/total,dead/total]
            return_json["by-life_status"] = {"dead":live/total,
                                             "live":dead/total}
            image += 1
            axes[image].pie(x=[live/total,dead/total], labels=["dead","live"], autopct='%.1f%%')
        plt.show()
        fig.savefig('image.png')
        if format_info == "json":
            return return_json,200
        elif format_info == "image":
            return make_response(send_file('image.png'),200)


# api.add_resource(HelloWorld,"/") 装置器声明方法二 "/"代表路径
if __name__ == "__main__":
    # manager.run()####
    app.run(host='127.0.0.1',debug=True,port=5000)
    pass
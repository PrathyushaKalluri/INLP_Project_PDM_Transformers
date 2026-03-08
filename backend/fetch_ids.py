from pymongo import MongoClient
c = MongoClient('mongodb://localhost:27017')
db = c['meeting_tasks']

print('=== USERS ===')
for u in db.users.find({}, {'_id':1,'email':1,'full_name':1}):
    print('  ' + u['email'] + ' -> ' + str(u['_id']))

print()
print('=== WORKSPACES ===')
for w in db.workspaces.find({}, {'_id':1,'name':1}):
    print('  ' + w['name'] + ' -> ' + str(w['_id']))

print()
print('=== TEAMS ===')
for t in db.teams.find({}, {'_id':1,'name':1}):
    print('  ' + t['name'] + ' -> ' + str(t['_id']))

print()
print('=== PROJECTS ===')
for p in db.projects.find({}, {'_id':1,'name':1}):
    print('  ' + p['name'] + ' -> ' + str(p['_id']))

print()
print('=== MEETINGS ===')
for m in db.meetings.find({}, {'_id':1,'title':1}):
    print('  ' + m['title'] + ' -> ' + str(m['_id']))

print()
print('=== TASKS ===')
for t in db.tasks.find({}, {'_id':1,'title':1,'status':1}):
    print('  [' + t['status'] + '] ' + t['title'][:50] + ' -> ' + str(t['_id']))

print()
print('=== TASK SUGGESTIONS (PENDING) ===')
for s in db.task_suggestions.find({'review_status':'PENDING'}, {'_id':1,'suggested_title':1}):
    print('  ' + s['suggested_title'][:55] + ' -> ' + str(s['_id']))

c.close()

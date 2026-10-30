"""Yörünge display values from existing task/row authorities; no mutations."""
import math
from atlas_view import observed_parts,number
from list_display import row_values


def gauge_limit(speed,peak=0):
    """Bytes/s in, MB/s scale out; grow in complete 50 MB/s steps."""
    return max(50,50*math.ceil(max(0,speed,peak)/1048576/50))


def telemetry(app,records):
    running=[];connections=[]
    for record in records:
        values=row_values(app,record)
        if values[8] not in ('İndiriliyor','Birleştiriliyor','Dönüştürülüyor'):continue
        running.append(record)
        connections.append(observed_parts(app,record)[1])
    return dict(active=len(running),connections=sum(connections) if all(value is not None for value in connections) else None)


def target(app,record):
    values=row_values(app,record);rows,active=observed_parts(app,record)
    return dict(id=record['id'],name=record['filename'],status=values[8],
        progress=min(1,max(0,float(values[5].rstrip('%'))/100)) if values[2]!='Bilinmiyor' or values[8]=='Tamamlandı' else None,
        amount=number(app,values[3])+' / '+number(app,values[2]),speed=number(app,values[6]),
        eta=values[7],queue=record.get('queue_name','Ana kuyruk'),rows=rows,connections=active)

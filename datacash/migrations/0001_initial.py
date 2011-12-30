# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'OrderTransaction'
        db.create_table('datacash_ordertransaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('order_number', self.gf('django.db.models.fields.CharField')(max_length=128, db_index=True)),
            ('method', self.gf('django.db.models.fields.CharField')(max_length=12)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=12, decimal_places=2, blank=True)),
            ('merchant_reference', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('datacash_reference', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('auth_code', self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('request_xml', self.gf('django.db.models.fields.TextField')()),
            ('response_xml', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('datacash', ['OrderTransaction'])


    def backwards(self, orm):
        
        # Deleting model 'OrderTransaction'
        db.delete_table('datacash_ordertransaction')


    models = {
        'datacash.ordertransaction': {
            'Meta': {'object_name': 'OrderTransaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '12', 'decimal_places': '2', 'blank': 'True'}),
            'auth_code': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'datacash_reference': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant_reference': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'method': ('django.db.models.fields.CharField', [], {'max_length': '12'}),
            'order_number': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'request_xml': ('django.db.models.fields.TextField', [], {}),
            'response_xml': ('django.db.models.fields.TextField', [], {}),
            'status': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['datacash']

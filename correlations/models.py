from db.models import Model, mongodb_init

class Buff(Model):
    table = "buff"
    
    @mongodb_init
    def __init__(self, user_id = '', interval = '', interval_start = '',
    interval_end = '', correlation = 0, aspects = {}, template_key = 'default'):
        self.user_id = user_id
        self.interval = interval
        self.interval_start = interval_start
        self.interval_end = interval_end
        self.correlation = correlation
        self.aspects = aspects
        self.template_key = template_key
        
    @property
    def strength(self):
        return abs(self.correlation)

class BuffTemplate(Model):
    table = "buff_template"
    
    @mongodb_init
    def __init__(self, text, key = 'default'):
        self.text = text
        self.key = key
    
    def __str__(self):
        if 'buff' in self and self.buff:
            return self.text.format(
                strength = self.buff.strength,
                interval = self.buff.interval,
                interval_start = self.buff.interval_start,
                interval_end = self.buff.interval_end,
                **self.buff.aspects
            )
        else:
            return self.text
            
    def set_buff(self, buff):
        self.buff = buff
            
    def save(self, *args, **kwargs):
        if 'buff' in self:
            raise Exception("Cannot save template when a buff has been set.")
        else:
            super(BuffTemplate, self).save(*args, **kwargs)

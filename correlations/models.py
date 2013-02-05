from db.models import Model, mongodb_init

class Buff(Model):
    table = "buff"
    
    @mongodb_init
    def __init__(self, user_id = '', interval = '', start = '',
    end = '', correlation = 0, aspects = {}, template_key = 'default'):
        self.user_id = user_id
        self.interval = interval
        self.start = start
        self.end = end
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
                start = self.buff.start,
                end = self.buff.end,
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

"""Shadow-free, ambient-dominant Workbench lighting for anatomical diagrams."""
def configure(scene):
    import bpy
    shading=scene.display.shading
    shading.light='STUDIO'
    shading.show_shadows=False
    shading.show_cavity=False
    shading.show_specular_highlight=False
    system=bpy.context.preferences.system
    # In-memory background-process settings only. Never save user preferences.
    system.use_studio_light_edit=True
    system.light_ambient=(.55,.55,.55)
    directions=[(.25,.45,.86),(-.65,.30,.70),(.4,-.5,.75),(0.,0.,-1.)]
    fills=[.45,.06,.04,.02]
    for light,direction,fill in zip(system.solid_lights,directions,fills):
        light.use=True
        light.diffuse_color=(fill,fill,fill)
        light.specular_color=(0.,0.,0.)
        light.smooth=.45
        light.direction=direction
    for obj in scene.objects:
        if hasattr(obj,'visible_shadow'):obj.visible_shadow=False
        if obj.type=='LIGHT' and hasattr(obj.data,'use_shadow'):obj.data.use_shadow=False
    return {'cast_shadows':False,'cavity_ao':False,'specular_highlights':False,
            'ambient_rgb':[.55,.55,.55],'diffuse_fill_strengths':fills,
            'user_preferences_saved':False}

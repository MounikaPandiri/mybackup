class catalog(object):
	def __init__(self):
		pass

	def version(self):
		return '1.0'

	def __flavor_create__(self,keyword='both'):
                mandatory_params={'vcpus','disk','name','ram'}
                optional_params={'is_public',"id","OS-FLV-EXT-DATA:ephemeral","swap"}
                params = {}
                params['mandatory_params'] = mandatory_params
                params['optional_params'] = optional_params
                return params

	def __create_network__(self,keyword='both'):
		mandatory_params={'network','cidr','subnet_name'}
		optional_params={'ip_version'}
		params={}
		params['mandatory_params'] = mandatory_params
		params['optional_params'] = optional_params
		return params
	
	def __create_service__(self,keyword='both'):
		mandatory_params={'name','qos','attributes'}
		optional_params={'description'}
		params = {}
		params['mandatory_params'] = mandatory_params
		params['optional_params'] = optional_params
		return params

	def __create_router__(self,keyword='both'):
                mandatory_params={'router_name'}
                optional_params={'external_network_name'}
                params = {}
                params['mandatory_params'] = mandatory_params
                params['optional_params'] = optional_params
                return params
		
	def __onboard__(self,keyword='both'):
		mandatory_params = {'serviceName','path'}
		params['mandatory_params'] = mandatory_params
		return params

        def __start_diagnostics__(self,keyword='both'):
                params = {}
                mandatory_params = {'nsd_id','files'}
                params['mandatory_params'] = mandatory_params
                return params 	

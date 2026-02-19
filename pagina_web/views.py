from django.shortcuts import render , redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from firebase_admin import firestore, auth
from config.firebase_connection import initialize_firebase
from functools import wraps

import requests
import os


db = initialize_firebase()

#  registro para que los usuarios puedan loggearse
def registro_usuario(request):
    mensaje = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = auth.create_user(
                email=email,
                password=password
            )

            db.collection('perfiles').document(user.uid).set({
                'email': email,
                'uid': user.uid,
                'rol': 'usuario',
                'fecha_registro': firestore.SERVER_TIMESTAMP
            })

            mensaje = f"✅ Usuario registrado éxitosamente {user.uid}"

        except Exception as e:
            # messages.error(os.error)
            mensaje = f"❌ Error!! No se pudo registrar el usuario: {str(e)}"

    return render(request, 'registro.html', {'mensaje': mensaje})


#requerimiento del login
def login_required_firebase(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'uid' not in request.session:
            messages.warning(request, "⚠️ Debes iniciar sesión.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


#login de usuario

def iniciar_sesion(request):
    if ('uid') in request.session:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        api_key =os.getenv('FIREBASE_WEB_API_KEY')

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        try:
            response = requests.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:
                request.session['uid']= data['localId']
                request.session['email'] = data['email']
                request.session['idToken'] = data['idToken']
                messages.success(request, f"✅ sesión iniciada.")
                return redirect('dashboard')
            else:
                error_message = data.get('error', {}).get('message', 'Error desconocido')
                
                errores_comunes = {
                    'INVALID_LOGIN_CREDENTIALS': 'La contraseña es incorrecta o el correo no es válido.',
                    'EMAIL_NOT_FOUND': 'Este correo no está registrado en el sistema.',
                    'USER_DISABLED': 'Esta cuenta ha sido inhabilitada por el administrador.',
                    'TOO_MANY_ATTEMPTS_TRY_LATER': 'Demasiados intentos fallidos. Espere unos minutos.'
                }
                mensaje_usuario = errores_comunes.get(error_message, "❎Error de autenticación revisa tus credenciales")
                messages.error(request, mensaje_usuario)

        except requests.exceptions.RequestException as e:
            messages.error(request, "❎Error de conexión con el servidor")
        except Exception as e:
            messages.error(request, f"Error inesperado: {str(e)}")
    return render(request, 'login.html')

#cerrarsesion de usuario
def cerrar_sesion(request):
    request.session.flush()
    messages.info(request, "✅ Has cerrado sesión.")
    return redirect('login')

#pagina principal (dashboard)
#verifica el login del usuario

@login_required_firebase
def dashboard(request):
    uid = request.session.get('uid')
    datos_usuario = {}
    libros = []

    try:
        doc_ref = db.collection('perfiles').document(uid)
        doc = doc_ref.get()

        if doc.exists:
            datos_usuario = doc.to_dict()
        else:
            datos_usuario = {
                'email': request.session.get('email'),
                'uid': request.session.get('uid'),
                'rol': '',
            }

        
        docs = db.collection('libros').where('usuario_uid', '==', uid).stream()

        for doc in docs:
            libro = doc.to_dict()
            libro['id'] = doc.id
            libros.append(libro)

    except Exception as e:
        messages.error(request, f"error al cargar los datos de la BD: {e}")

    return render(request, 'dashboard.html', {
        'datos_usuario': datos_usuario,
        'libros': libros 
    })

@login_required_firebase
def añadir_libro(request):
    if request.method == 'POST':
        autor = request.POST.get('autor')
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        fecha = request.POST.get('fecha')
        opinion = request.POST.get('opinion')
        recomendacion = request.POST.get('recomendacion')
        uid = request.session.get('uid')

        try: 
            db.collection('libros').add({
                'autor': autor,
                'titulo': titulo,
                'descripcion': descripcion,
                'fecha': fecha,
                'opinion': opinion,
                'recomendacion': recomendacion,
                'usuario_uid': uid,
                'fecha_creacion': firestore.SERVER_TIMESTAMP
            })
            messages.success(request, "✅ Libro añadido con éxito.")
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"❌ Error al añadir libro: {e}")
    return render(request, 'libros/añadir.html')

@login_required_firebase
def eliminar_libro(request, libro_id):
    try: 
        db.collection('libros').document(libro_id).delete()
        messages.success(request, "✅ Libro eliminado.")
    except Exception as e:
        messages.error(request, f"❌ Error al eliminar libro: {e}")
    return redirect('dashboard')

@login_required_firebase
def editar_libro(request, libro_id):
    uid  = request.session.get('uid')
    libro_ref = db.collection('libros').document(libro_id)

    try:
        doc = libro_ref.get()
        if not doc.exists:
            messages.error(request, "❌ Libro no encontrado.")
            return redirect('dashboard')

        libro = doc.to_dict()
        if libro.get('usuario_uid') != uid:
            messages.error(request, "❌ No tienes permiso para editar este libro.")
            return redirect('dashboard')
        
        if request.method == 'POST':
            libro_ref.update({
                'titulo': request.POST.get('titulo'),
                'descripcion': request.POST.get('descripcion'),
                'fecha': request.POST.get('fecha'),
                'opinion': request.POST.get('opinion'),
                'recomendacion': request.POST.get('recomendacion'),
            })
            messages.success(request, "✅ Libro actualizado.")
            return redirect('dashboard')
    except Exception as e:
        messages.error(request, f"❌ Error al editar libro: {e}")
        return redirect('dashboard')
    return render(request, 'libros/editar.html', {'libro': libro,'id': libro_id}) 
 
  
    